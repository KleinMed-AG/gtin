# gtin/ UDI Label Generator

Dieses Repository erzeugt automatisiert UDI-Etiketten gemäß Arbeitsanweisung
"AA_UDI Etiketten Erstellung" und ersetzt vollständig Excel + Word Workflow.

## Features
- GitHub Pages Frontend zur Job-Erstellung
- GitHub Action zum Generieren aller UDI-Labels
- Automatische Seriennummern
- Lokale QR-Code Generierung (MDR-konform)
- PDF-Erstellung mit ReportLab
- Audit-Trail über Commits

## Workflow
1. User öffnet GitHub Pages UI (`/docs`)
2. Füllt Formular aus
3. YAML-Jobfile wird erzeugt
4. GitHub Action generiert PDFs
5. PDFs erscheinen unter `/output` und im Action-Artifact

## Technologie
- Python
- ReportLab
- qrcode
- GitHub Actions
- GitHub Pages
