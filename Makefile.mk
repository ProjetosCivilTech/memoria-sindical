.PHONY: help check extract consolidate compare validate build all

help:
	@echo "Alvos disponíveis:"
	@echo "  check         audita PDFs vs dicionário"
	@echo "  extract       PDFs -> data/raw/*.json"
	@echo "  consolidate   data/raw/*.json -> data/build/*"
	@echo "  compare       gera comparacoes FENTECT x FINDECT"
	@echo "  validate      valida schema de data/raw/*.json"
	@echo "  build         consolidate + compare"
	@echo "  all           check + extract + build + validate"

check:
	python -m scripts.check_pdfs

extract:
	python -m scripts.extract

consolidate:
	python -m scripts.consolidate

compare:
	python -m scripts.compare

validate:
	python -m scripts.validate

build: consolidate compare

all: check extract build validate