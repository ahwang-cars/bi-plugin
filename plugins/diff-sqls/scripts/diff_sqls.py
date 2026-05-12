#!/usr/bin/env python3
"""
Diff Redshift result sets between two SQL scripts.

Each side (`--a` / `--b`) takes one or more SQL files, concatenated and run in
order on a dedicated Redshift connection (so `CREATE TEMPORARY TABLE` carries
across files within a side). The final statement on each side must be — or be
overridden by `--final-query` to be — a SELECT. That SELECT's rows are what we
compare.

Typical patterns:

    # Two versions of an Initial SQL that share the same Custom SQL:
    diff_sqls.py --a initial_v1.sql custom.sql --b initial_v2.sql custom.sql

    # Two standalone SELECTs:
    diff_sqls.py --a old.sql --b new.sql

    # Initial-only files, diff a specific temp table:
    diff_sqls.py --a initial_v1.sql --b initial_v2.sql \\
                 --final-query "SELECT * FROM leads_final"

Credentials are auto-discovered from (in order):
    1. --config <path>, if given
    2. ~/.tableau-config.json   (shared with tableau-sql)
    3. ~/.diff-sqls-config.json
Env vars (REDSHIFT_HOST/PORT/DATABASE/USER/PASSWORD) fill any gaps.

Schema in the config file:
    {
      "connection_credentials": {"username": "...", "password": "..."},
      "redshift": {"host": "...", "port": 5439, "database": "dw"}
    }
The `connection_credentials` block is the same one tableau-sql reads;
`redshift` is a new top-level block it ignores. user/password may also live
under "redshift" if you'd rather keep diff-sqls self-contained.

Output: same markdown printed to stdout is also saved to a file. Default path is
`diff-<labelA>-vs-<labelB>-<UTC-timestamp>.md` in cwd; override with `--output`.
The saved file is the artifact to paste into a ticket as proof of validation.

Exit codes: 0 if row count and every column aggregate matches, 1 otherwise.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

import redshift_connector
import sqlparse


class _Tee:
    """Writer that fans writes out to multiple streams (e.g. stdout + a file).
    Keeps real-time output so a crash mid-run still leaves a partial report."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for st in self._streams:
            st.write(s)
        return len(s)

    def flush(self):
        for st in self._streams:
            st.flush()


def _slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "x"


def _default_output_path(label_a, label_b):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"diff-{_slug(label_a)}-vs-{_slug(label_b)}-{ts}.md"


# Auto-discovery order. Shared with tableau-sql so users only maintain
# one creds file. The user/password are pulled from `connection_credentials`
# (tableau-sql's existing schema); host/port/database come from a new
# top-level `redshift` block that tableau-sql ignores.
DEFAULT_CONFIG_PATHS = [
    os.path.expanduser("~/.tableau-config.json"),
    os.path.expanduser("~/.diff-sqls-config.json"),
]


def _resolve_config_path(explicit):
    if explicit:
        if not os.path.exists(explicit):
            sys.exit(f"Config file not found: {explicit}")
        return explicit
    for p in DEFAULT_CONFIG_PATHS:
        if os.path.exists(p):
            return p
    return None


def load_creds(config_path):
    rs = {}
    conn = {}
    path = _resolve_config_path(config_path)
    if path:
        with open(path) as f:
            data = json.load(f)
        rs = data.get("redshift") or {}
        conn = data.get("connection_credentials") or {}

    creds = {
        "host": rs.get("host") or os.environ.get("REDSHIFT_HOST"),
        "port": int(rs.get("port") or os.environ.get("REDSHIFT_PORT") or 5439),
        "database": rs.get("database") or os.environ.get("REDSHIFT_DATABASE") or "dw",
        "user": rs.get("user") or conn.get("username") or os.environ.get("REDSHIFT_USER"),
        "password": rs.get("password") or conn.get("password") or os.environ.get("REDSHIFT_PASSWORD"),
    }
    missing = [k for k in ("host", "user", "password") if not creds[k]]
    if missing:
        searched = ", ".join(DEFAULT_CONFIG_PATHS)
        sys.exit(
            f"Missing Redshift credentials: {', '.join(missing)}.\n"
            f"Auto-discovery searched: {searched}\n"
            "Add a top-level \"redshift\" block (host/port/database) to your "
            "~/.tableau-config.json, or set REDSHIFT_HOST/USER/PASSWORD env vars, "
            "or pass --config <path>."
        )
    return creds


def connect(creds):
    return redshift_connector.connect(**creds)


def read_files(paths):
    parts = []
    for p in paths:
        with open(p) as f:
            parts.append(f.read())
    return "\n".join(parts)


def split_statements(sql):
    """Split a SQL blob into individual statements, dropping empties and
    comment-only blocks."""
    out = []
    for stmt in sqlparse.split(sql):
        stmt = stmt.strip().rstrip(";").strip()
        if not stmt:
            continue
        if not sqlparse.format(stmt, strip_comments=True).strip():
            continue
        out.append(stmt)
    return out


def is_select(stmt):
    stripped = sqlparse.format(stmt, strip_comments=True).strip().lower()
    return stripped.startswith("select") or stripped.startswith("with")


def prepare_side(conn, paths, final_query):
    """Execute setup statements on `conn`; return the SELECT to compare."""
    stmts = split_statements(read_files(paths))
    if not stmts:
        sys.exit(f"No SQL statements found in: {paths}")

    if final_query:
        setup = stmts
        query = final_query.strip().rstrip(";").strip()
    else:
        if not is_select(stmts[-1]):
            sys.exit(
                f"Last statement in {paths} is not a SELECT/WITH. "
                "Pair the file with one that ends in a SELECT, or pass --final-query."
            )
        setup, query = stmts[:-1], stmts[-1]

    with conn.cursor() as cur:
        for stmt in setup:
            cur.execute(stmt)
    return query


def run_query(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        if isinstance(columns[0], bytes):
            columns = [c.decode() for c in columns]
        rows = cur.fetchall()
    return columns, rows


def md_table(headers, rows):
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
    return "\n".join(lines)


def _wrap(prefix, query, suffix=""):
    """Wrap a subquery with newlines so trailing `--` line comments don't swallow
    the suffix. Without the leading/trailing newlines, `SELECT ... FROM (foo
    --comment) t` parses `) t` as part of the comment."""
    return f"{prefix} (\n{query}\n) t{suffix}"


def compare(conn_a, query_a, label_a, conn_b, query_b, label_b, row_diff_limit):
    # Row count
    _, cnt_a = run_query(conn_a, _wrap("SELECT COUNT(*) FROM", query_a))
    _, cnt_b = run_query(conn_b, _wrap("SELECT COUNT(*) FROM", query_b))
    rows_a, rows_b = cnt_a[0][0], cnt_b[0][0]
    row_match = rows_a == rows_b

    print("### Row count")
    print(
        md_table(
            ["Side", "Rows"],
            [
                [label_a, f"{rows_a:,}"],
                [label_b, f"{rows_b:,}"],
                ["Status", "MATCH" if row_match else "DIFF"],
            ],
        )
    )
    print()

    # Column aggregates (use B's schema as the canonical column list)
    cols, _ = run_query(conn_b, _wrap("SELECT * FROM", query_b, " LIMIT 0"))
    agg_parts = ["COUNT(*) AS _total_rows"]
    for c in cols:
        agg_parts.append(f'COUNT(DISTINCT "{c}") AS "_distinct_{c}"')
        agg_parts.append(f'COUNT(CASE WHEN "{c}" IS NULL THEN 1 END) AS "_null_{c}"')
    agg_select = ", ".join(agg_parts)

    agg_cols, agg_a = run_query(conn_a, _wrap(f"SELECT {agg_select} FROM", query_a))
    _, agg_b = run_query(conn_b, _wrap(f"SELECT {agg_select} FROM", query_b))

    print("### Column aggregates")
    table_rows = []
    agg_diffs = 0
    for i, col in enumerate(agg_cols):
        va, vb = agg_a[0][i], agg_b[0][i]
        match = va == vb
        if not match:
            agg_diffs += 1
        table_rows.append([col.lstrip("_"), va, vb, "MATCH" if match else "DIFF"])
    print(md_table(["Metric", label_a, label_b, "Status"], table_rows))
    print()
    print(f"_Aggregate diffs: {agg_diffs} of {len(agg_cols)} metrics._\n")

    # Row-level set diff (small results only)
    if rows_a <= row_diff_limit and rows_b <= row_diff_limit:
        print("### Row-level diff")
        data_cols, data_a = run_query(conn_a, _wrap("SELECT * FROM", query_a, " ORDER BY 1"))
        _, data_b = run_query(conn_b, _wrap("SELECT * FROM", query_b, " ORDER BY 1"))
        set_a = set(map(tuple, data_a))
        set_b = set(map(tuple, data_b))
        only_a = set_a - set_b
        only_b = set_b - set_a
        if not only_a and not only_b:
            print(f"All rows match between {label_a} and {label_b}.\n")
        else:
            if only_a:
                print(f"**Rows in {label_a} only ({len(only_a)}):**")
                print(md_table(data_cols, sorted(only_a)))
                print()
            if only_b:
                print(f"**Rows in {label_b} only ({len(only_b)}):**")
                print(md_table(data_cols, sorted(only_b)))
                print()
    else:
        print(
            f"> Row-level diff skipped ({label_a}: {rows_a:,}, {label_b}: {rows_b:,} "
            f"rows; limit is {row_diff_limit:,}). Column aggregates above are the primary check.\n"
        )

    return row_match and agg_diffs == 0


def main():
    p = argparse.ArgumentParser(
        description="Diff Redshift result sets between two SQL scripts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--a", nargs="+", required=True, metavar="FILE",
                   help="Side A: one or more SQL files run in order")
    p.add_argument("--b", nargs="+", required=True, metavar="FILE",
                   help="Side B: one or more SQL files run in order")
    p.add_argument("--label-a", default="A", help="Label for side A in the output (default: A)")
    p.add_argument("--label-b", default="B", help="Label for side B in the output (default: B)")
    p.add_argument("--final-query",
                   help="Override the final SELECT. Useful when the files only set up temp tables.")
    p.add_argument("--row-diff-limit", type=int, default=1000,
                   help="Skip row-level set diff when either side exceeds this row count (default: 1000)")
    p.add_argument("--config", help="Path to a JSON config with Redshift creds (alternative to env vars)")
    p.add_argument("--output", metavar="PATH",
                   help="Write the markdown report here. Defaults to "
                        "diff-<labelA>-vs-<labelB>-<UTC-timestamp>.md in cwd.")
    args = p.parse_args()

    for path in [*args.a, *args.b]:
        if not os.path.exists(path):
            sys.exit(f"File not found: {path}")

    creds = load_creds(args.config)

    out_path = os.path.abspath(args.output or _default_output_path(args.label_a, args.label_b))
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    out_file = open(out_path, "w")
    real_stdout = sys.stdout
    sys.stdout = _Tee(real_stdout, out_file)
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"## Diff: `{args.label_a}` vs `{args.label_b}`")
        print(f"- {args.label_a}: {' + '.join(args.a)}")
        print(f"- {args.label_b}: {' + '.join(args.b)}")
        if args.final_query:
            print(f"- Final query (both sides): `{args.final_query}`")
        print(f"_Run at {now}_\n")

        conn_a = connect(creds)
        conn_b = connect(creds)
        try:
            query_a = prepare_side(conn_a, args.a, args.final_query)
            query_b = prepare_side(conn_b, args.b, args.final_query)
            ok = compare(conn_a, query_a, args.label_a, conn_b, query_b, args.label_b,
                         args.row_diff_limit)
        finally:
            conn_a.close()
            conn_b.close()
    finally:
        sys.stdout = real_stdout
        out_file.close()

    print(f"Saved diff report to: {out_path}", file=sys.stderr)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
