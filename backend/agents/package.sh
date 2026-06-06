#!/bin/bash
set -e

echo "📦 Packaging Lambda agents..."

AGENTS_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$AGENTS_DIR"

for agent in planner tagger reporter scheduler; do
    echo "Packaging $agent..."

    TEMP_DIR="/tmp/${agent}_package"
    rm -rf $TEMP_DIR
    mkdir -p $TEMP_DIR

    cp ${agent}.py $TEMP_DIR/

    pip install boto3 httpx \
        --target $TEMP_DIR/ \
        --quiet \
        --upgrade

    cd $TEMP_DIR
    zip -r ${AGENTS_DIR}/${agent}.zip . > /dev/null
    cd "$AGENTS_DIR"

    rm -rf $TEMP_DIR
    echo "✅ ${agent}.zip created"
done

echo ""
echo "✅ All agents packaged!"
ls -lh *.zip