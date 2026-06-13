# ===========================================================================
# Makefile — shortcuts for common project commands.
# Run `make <target>`. Run `make help` to list targets.
#
# Why a Makefile? So you (and CI) type `make verify` instead of remembering
# long multi-flag commands. Each target is documented with `## comment` which
# the `help` target prints automatically.
# ===========================================================================

.PHONY: help setup verify extract load dbt-build dbt-test dbt-docs mcp streamlit lint

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:  ## Install Python dependencies for the extractors
	pip install -r extractors/requirements.txt

verify:  ## Verify connectivity to ADLS Gen2 and Snowflake (Phase 1 check)
	python -m extractors.verify_connectivity

extract:  ## Run all extractors (writes JSON locally)
	cd extractors && python -m extractors.run_all

load:  ## Load staged JSON into Snowflake Bronze via COPY INTO
	cd extractors && python -m extractors.loader

dbt-build:  ## Run + test all dbt models
	cd dbt_project && dbt build

dbt-test:  ## Run dbt tests only
	cd dbt_project && dbt test

dbt-docs:  ## Generate and serve the dbt docs site
	cd dbt_project && dbt docs generate && dbt docs serve

mcp:  ## Start the MCP server
	cd mcp_server && python server.py

streamlit:  ## Start the Streamlit dashboard
	cd streamlit && streamlit run app.py

lint:  ## Lint Python code
	ruff check extractors/ mcp_server/
