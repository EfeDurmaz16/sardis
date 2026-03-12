#!/bin/bash
export PATH="/Users/efebarandurmaz/.nvm/versions/node/v20.19.5/bin:$PATH"
cd "$(dirname "$0")"
npx ts-mocha -p ./tsconfig.json -t 1000000 tests/**/*.ts
