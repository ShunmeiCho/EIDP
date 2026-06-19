# Source Check

Date: 2026-06-20

## Artifact Inventory

The previous root-level `UI-example/` folder contained:

- `EIDP 運用コンソール (standalone).html`
- `.DS_Store`

No `.dc.html` source file and no `support.js` runtime file were present when
the prototype was moved into this design package.

## Old-Term Scan

The standalone HTML was scanned before migration with this pattern set:

```text
DB転記
要確認キュー
Excelプレビュー
週次運用フロー
学部・学科別データ
令和8年度で確定
スキップ
```

Result:

| Term | Count |
| --- | ---: |
| `DB転記` | 0 |
| `要確認キュー` | 0 |
| `Excelプレビュー` | 0 |
| `週次運用フロー` | 0 |
| `学部・学科別データ` | 0 |
| `令和8年度で確定` | 1 |
| `スキップ` | 0 |

`令和8年度で確定` remains as visible fiscal-year confirmation copy in the
prototype. It is not treated as production state.

## Generated Artifact Rule

Do not hand-edit the standalone HTML to clean generated code. Update the design
source and regenerate the artifact when a `.dc.html` source is available.
