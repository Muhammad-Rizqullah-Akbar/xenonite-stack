.PHONY: help check verify test install install-mr-robot uninstall docker-up docker-up-gpu docker-down

PY ?= python

help:
	@echo "Xenonite 4-Layer Stack - Master Commands:"
	@echo "  make check            : Run Pre-Flight System Audit across L1-L4"
	@echo "  make verify           : Run silent-filtered security, hooks, and MCP smoke suite"
	@echo "  make test             : Run full Python unit test suite"
	@echo "  make install          : Install MCP + Anti-Churn Hooks + Standard Rule into ~/.gemini/config"
	@echo "  make install-mr-robot : Install with optional Mr. Robot persona rule"
	@echo "  make uninstall        : Cleanly remove Xenonite entries from ~/.gemini/config"
	@echo "  make docker-up        : Start full self-hosted Docker stack (CPU)"
	@echo "  make docker-up-gpu    : Start full self-hosted Docker stack (NVIDIA GPU)"
	@echo "  make docker-down      : Stop self-hosted Docker stack"

check:
	@$(PY) -m xenonite_stack check

verify:
	@$(PY) -m xenonite_stack verify --mode all

test:
	@$(PY) -m unittest discover -s tests -p "test_*.py" -v

install:
	@$(PY) -m xenonite_stack install --persona standard

install-mr-robot:
	@$(PY) -m xenonite_stack install --persona mr-robot

uninstall:
	@$(PY) -m xenonite_stack uninstall

docker-up:
	@$(PY) -m xenonite_stack docker up full

docker-up-gpu:
	@$(PY) -m xenonite_stack docker up full --gpu

docker-down:
	@$(PY) -m xenonite_stack docker down full
