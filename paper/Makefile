# EthioMorph Paper - Build System
# ================================
# Requires: XeLaTeX (for Ge'ez font support)
# Font: Abyssinica SIL (install from fonts.google.com or SIL)

PAPER = ethiomorph_paper
LATEX = xelatex
BIBTEX = bibtex

.PHONY: all clean view

all: $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex references.bib
	$(LATEX) $(PAPER)
	$(BIBTEX) $(PAPER) || true
	$(LATEX) $(PAPER)
	$(LATEX) $(PAPER)

clean:
	rm -f $(PAPER).aux $(PAPER).bbl $(PAPER).blg $(PAPER).log \
	      $(PAPER).out $(PAPER).pdf $(PAPER).toc $(PAPER).lof \
	      $(PAPER).lot $(PAPER).synctex.gz

view: $(PAPER).pdf
	open $(PAPER).pdf || xdg-open $(PAPER).pdf

# Quick build without bibliography
quick:
	$(LATEX) $(PAPER)
