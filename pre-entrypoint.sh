#!/bin/bash
set -e

TEMPLATE="/etc/odoo/odoo.conf.tmpl"

echo "Generated odoo.conf:"

: > "$ODOO_RC"  # очищаем файл

while IFS= read -r line; do
    if [[ "$line" =~ \$(\{?([A-Za-z_][A-Za-z0-9_]*)\}?) ]]; then
        var="${BASH_REMATCH[2]}"
        value="${!var}"

        if [[ -z "$value" ]]; then
            echo "skip (no env): $line"
            continue
        fi

        eval "echo \"${line}\"" >> "$ODOO_RC"
    else
        echo "$line" >> "$ODOO_RC"
    fi
done < "$TEMPLATE"

cat $ODOO_RC

exec /entrypoint.sh "$@"
