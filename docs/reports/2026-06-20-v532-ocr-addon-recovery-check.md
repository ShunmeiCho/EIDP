# v532 OCR Add-on Recovery Check

Date: 2026-06-20
Branch: `main`
Scope: read-only search for an existing Windows OCR add-on or reusable
Tesseract payload after the v532 Windows side-by-side smoke.

## Verdict

No reusable OCR add-on ZIP or Windows Tesseract payload was found in the checked
Mac, external-SSD, or Windows locations. The v532 OCR runtime proof remains
blocked unless an approved OCR add-on ZIP is restored, rebuilt from an approved
Windows Tesseract source, or OCR is explicitly removed from the selected v1.0
release scope.

## Checks Performed

Mac / external SSD:

- Searched `/Volumes/M1nG-ssd/EIDP-artifacts` and
  `/Users/shunmei/workspace/EIDP` for `*ocr*.zip` and `*tesseract*.zip`.
  Result: no matching files.
- Searched the same locations for `tesseract.exe`, `jpn.traineddata`, and
  `jpn_vert.traineddata`. Result: no reusable Windows payload files.
- Checked `/opt/homebrew/share/tessdata`. Result: local Homebrew tessdata exists
  and includes `jpn.traineddata`, `jpn_vert.traineddata`, and `configs/tsv`, but
  this does not provide the required Windows `tesseract.exe` and DLL payload.

Windows operator machine via `ssh win`:

- Searched `C:\EIDP-staging` and `C:\Users\cyo20` for OCR/Tesseract ZIP files.
  Result: no matching add-on ZIP.
- Searched `C:\Program Files`, `C:\Program Files (x86)`,
  `C:\EIDP-staging`, and `C:\Users\cyo20` for:
  - `tesseract.exe`
  - `jpn.traineddata`
  - `jpn_vert.traineddata`
  - `tessdata\configs\tsv`

  Result JSON:

  ```json
  {"tesseract":[],"jpn":[],"jpn_vert":[],"tsv":[]}
  ```

## Packaging Boundary

The repository still contains the deterministic packager at
`scripts/build_ocr_addon_zip.py`. It intentionally does not download binaries.
It requires an approved prepared source layout:

```text
ocr-addon/tesseract/tesseract.exe
ocr-addon/tessdata/jpn.traineddata
ocr-addon/tessdata/configs/tsv
```

Historical reports mention `dist/eidp-ocr-addon-windows-v497-smoke.zip` and
earlier OCR runtime proofs, but that ZIP is not currently present in the checked
Mac/external-SSD/Windows locations.

## Release Impact

- v532 remains the latest complete non-OCR Windows side-by-side smoke.
- v526 remains the latest package family with complete OCR runtime proof.
- Do not treat v532 as OCR-runtime proven until a current add-on ZIP is present
  and `scripts\validate_windows_install.py . --require-ocr-runtime --json`
  returns `ok=true` on Windows.
