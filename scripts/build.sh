#!/usr/bin/env bash
# build the AEPs
# For development purposes, it's best to lay out the other aep repositories
# side by side from the primary AEPs. If so, this script will use the
# site-generator and api-linter from those sibling directories.
# Otherwise, it will clone dependencies.
set -x
export AEP_LOCATION="${PWD}"

declare -A repos

repos=(
    [site_generator]="site-generator"
    [api_linter]="api-linter"
    [aep_openapi_linter]="aep-openapi-linter"
)

for varName in "${!repos[@]}"; do
    repoName="${repos[$varName]}"
    if [ -d ${AEP_LOCATION}/../${repoName} ]; then
        eval "$varName=${AEP_LOCATION}/../${repoName}"
    else
        eval "$varName=/tmp/${repoName}"
        if [ ! -d "${varName}" ]; then
            git clone https://github.com/aep-dev/$repoName.git "${!varName}"
        fi
    fi
done

cd "${site_generator}" || exit
# make rules / website folder
mkdir -p src/content/docs/tooling/linter/rules
mkdir -p src/content/docs/tooling/openapi-linter/rules
mkdir -p src/content/docs/tooling/website
npm install
npx playwright install --with-deps chromium
npm run generate
npm run build
