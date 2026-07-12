# EIDP Operations Console Demo Prototype

This directory contains the EIDP operator-console visual/demo prototype.

## Role

This prototype is a design reference and stakeholder demo artifact. It defines:

- page naming and operator-facing Japanese copy
- dashboard KPI presentation
- official PDF collection, PDF review, fiscal-year review, and Excel export flow
- school queue layout and review-lane language
- Streamlit production UI acceptance direction

It is not production UI code.

## Canonical demo file

Open:

`eidp-operations-console.demo.standalone.html`

This standalone file is for local preview and stakeholder demos. It should not
be embedded into Streamlit or served as the production application.

## Missing editable source

The previous `UI-example/` folder currently contained only the standalone HTML
artifact. No `.dc.html` source file or `support.js` runtime file was present at
the time this design package was created.

If the editable `.dc.html` and generated `support.js` are added later, keep them
in this directory and follow these rules:

- `.dc.html` is the editable design source.
- `support.js` is generated prototype runtime.
- Do not edit `support.js` manually.
- Do not import `support.js` into `src/eidp`.

## Do Not

- Do not connect this HTML directly to SQLite.
- Do not copy generated JavaScript into `src/eidp`.
- Do not treat mock numbers as business truth or test fixtures.
- Do not package this prototype as the production operator UI.
- Do not embed the standalone HTML into Streamlit with an iframe.

## Production Implementation Target

Production UI remains Streamlit-based under:

`src/eidp/review/`

Future package naming may move toward:

`src/eidp/operator_ui/`

Use this prototype as the design and copy reference, not as runtime source.

## Related Files

- `ui-contract.md`: page, label, status, and ViewModel contract seed.
- `implementation-map.md`: prototype-to-Streamlit implementation map.
- `source-check.md`: current artifact inventory and old-term scan result.
