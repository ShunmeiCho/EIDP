from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "propose_no_url_corporation_domains.py"
spec = importlib.util.spec_from_file_location("propose_no_url_corporation_domains", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_propose_candidates_uses_only_corporation_evidence_and_skips_existing(tmp_path: Path) -> None:
    gap = tmp_path / "gap.json"
    gap.write_text(
        json.dumps(
            {
                "no_url_corporation_buckets": [
                    {
                        "corporation_name": "八文字学園",
                        "schools": 4,
                        "prefectures": {"茨城県": 4},
                        "examples": [{"school_id": 420, "school_name": "水戸経理専門学校"}],
                    },
                    {
                        "corporation_name": "学校法人専用ページ",
                        "schools": 3,
                        "prefectures": {"東京都": 3},
                        "examples": [],
                    },
                    {
                        "corporation_name": "既存法人",
                        "schools": 2,
                        "prefectures": {"東京都": 2},
                        "examples": [],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    discovered = tmp_path / "discovered-urls-50.csv"
    discovered.write_text(
        "id,prefecture,corporation,school_name,url_candidate_1,confidence,url_type,http_status,notes\n"
        "1,茨城県,八文字学園,水戸看護福祉専門学校,https://www.mito.ac.jp/,0.85,corporation,200,group site\n"
        "2,東京都,学校法人専用ページ,A専門学校,https://example.ac.jp/a/,0.95,corporation_subpage,200,school page\n"
        "3,東京都,既存法人,B専門学校,https://existing.example/,0.95,corporation,200,already registered\n",
        encoding="utf-8",
    )
    existing = tmp_path / "corporation_domains.csv"
    existing.write_text(
        "corporation_name,domain_url,notes\n"
        "既存法人,https://existing.example/,\n",
        encoding="utf-8",
    )

    proposals = module.propose_candidates(
        gap_analysis_json=gap,
        discovered_urls_csv=discovered,
        corporation_domains_csv=existing,
    )

    assert proposals == [
        {
            "corporation_name": "八文字学園",
            "candidate_url": "https://www.mito.ac.jp/",
            "no_url_schools": 4,
            "prefectures": {"茨城県": 4},
            "examples": [{"school_id": 420, "school_name": "水戸経理専門学校"}],
            "evidence_school_name": "水戸看護福祉専門学校",
            "evidence_prefecture": "茨城県",
            "evidence_confidence": 0.85,
            "evidence_http_status": "200",
            "evidence_notes": "group site",
        }
    ]


def test_main_writes_output_json(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    data_dir = tmp_path / "data"
    url_dir = data_dir / "url-discovery"
    url_dir.mkdir(parents=True)
    gap = tmp_path / "gap.json"
    output = tmp_path / "proposals.json"
    gap.write_text(
        json.dumps(
            {
                "no_url_corporation_buckets": [
                    {"corporation_name": "八文字学園", "schools": 4, "prefectures": {}, "examples": []}
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (url_dir / "discovered-urls-50.csv").write_text(
        "id,prefecture,corporation,school_name,url_candidate_1,confidence,url_type,http_status,notes\n"
        "1,茨城県,八文字学園,水戸看護福祉専門学校,https://www.mito.ac.jp/,0.85,corporation,200,group site\n",
        encoding="utf-8",
    )
    (url_dir / "corporation_domains.csv").write_text("corporation_name,domain_url,notes\n", encoding="utf-8")

    rc = module.main([str(gap), "--data-dir", str(data_dir), "--output", str(output)])

    assert rc == 0
    assert json.loads(output.read_text(encoding="utf-8"))[0]["corporation_name"] == "八文字学園"
    assert "proposals=1" in capsys.readouterr().out
