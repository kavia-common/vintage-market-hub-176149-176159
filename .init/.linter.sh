#!/bin/bash
cd /home/kavia/workspace/code-generation/vintage-market-hub-176149-176159/ecommerce_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

