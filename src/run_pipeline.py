#!/usr/bin/env python3
"""
日本招聘案件データ抽出パイプライン — ルール駆動版

ルールライブラリ (data/rules/field_rules.json) からルールをロードし、
各フィールドに適用して抽出を行う。完全ルールベース、LLM不使用。
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.models import (
    RecruitmentCase, Location, Rate, Period, TradeFlow,
    JapaneseLevelInfo, EnglishLevelInfo, WorkingHours, SourceInfo,
)
from src.common.utils import convert_jp_date, generate_document_id
from src.preprocessor.text_normalizer import JapaneseTextNormalizer

normalizer = JapaneseTextNormalizer()

# ── ルールローダー ──

class RuleLibrary:
    """ルールライブラリをロードし、各フィールドにルールを提供する。"""

    def __init__(self, rules_path: str | Path):
        with open(rules_path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.rules = self.data["rules"]
        self.post = self.data.get("post_process", {})

    def get_rules(self, field: str) -> list[dict]:
        """特定フィールドの全ルールを取得。"""
        return self.rules.get(field, [])

    def get_post_process(self, field: str) -> dict:
        """フィールドの後処理設定を取得。マッピングあり。"""
        field_map = {
            "skill_requirement": "skill_requirement",
            "preferred_skills": "preferred_skills",
        }
        key = field_map.get(field, field)
        return self.post.get(key, {})


# ── ルール実行エンジン ──

class RuleEngine:
    """ルールを実行してフィールド値を抽出する。"""

    def __init__(self, rules_path: str | Path):
        self.library = RuleLibrary(rules_path)
        self.normalizer = JapaneseTextNormalizer()

    def extract_period(self, text: str) -> Period:
        """期間を抽出。"""
        rules = self.library.get_rules("period")
        now = datetime.now()

        for rule in rules:
            m = re.search(rule["pattern"], text)
            if not m:
                continue

            rid = rule["id"]
            groups = m.groups()

            # period_001: YYYY/MM/DD - YYYY/MM/DD
            if rid == "period_001" and len(groups) >= 5:
                try:
                    sd = f"{int(groups[0]):04d}-{int(groups[1]):02d}-{int(groups[2] or 1):02d}"
                    ed = f"{int(groups[3]):04d}-{int(groups[4]):02d}-{int(groups[5] or 1):02d}"
                    return Period(start_date=sd, end_date=ed, note=m.group())
                except:  # noqa: E722
                    continue

            # period_002: YYYY/MM/DD - (long term)
            if rid == "period_002" and len(groups) >= 2:
                try:
                    sd = f"{int(groups[0]):04d}-{int(groups[1]):02d}-{int(groups[2] or 1):02d}"
                    return Period(start_date=sd, long_term=True, note=m.group())
                except:  # noqa: E722
                    continue

            # period_003: YYYY年M月 - YYYY年M月
            if rid == "period_003" and len(groups) >= 3:
                try:
                    sd = f"{int(groups[0]):04d}-{int(groups[1]):02d}-01"
                    ed = f"{int(groups[2]):04d}-{int(groups[3]):02d}-01"
                    return Period(start_date=sd, end_date=ed, note=m.group())
                except:  # noqa: E722
                    continue

            # period_004: M月〜長期
            if rid == "period_004":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                sd = f"{year}-{month:02d}-01"
                return Period(start_date=sd, long_term=True, note=m.group())

            # period_005: M月开始
            if rid == "period_005":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                sd = f"{year}-{month:02d}-01"
                return Period(start_date=sd, note=m.group())

            # period_006: 即日
            if rid == "period_006":
                return Period(start_date=now.strftime("%Y-%m-%d"), note="即日")

            # period_007: 随時
            if rid == "period_007":
                return Period(start_date=now.strftime("%Y-%m-%d"), note="随時")

            # period_008: Immediate
            if rid == "period_008":
                return Period(start_date=now.strftime("%Y-%m-%d"), note="Immediate start")

            # period_009: M月〜M月 (year inferred)
            if rid == "period_009":
                m1, m2 = int(groups[0]), int(groups[1])
                y1 = now.year
                if m1 < now.month:
                    y1 += 1
                y2 = y1 if m2 >= m1 else y1 + 1
                return Period(
                    start_date=f"{y1}-{m1:02d}-01",
                    end_date=f"{y2}-{m2:02d}-01",
                    note=m.group()
                )

            # period_010: 即日 or M月
            if rid == "period_010":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                return Period(
                    start_date=now.strftime("%Y-%m-%d"),
                    long_term=True,
                    note=m.group()
                )

            # period_011: M月案件
            if rid == "period_011":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                return Period(start_date=f"{year}-{month:02d}-01", note=m.group())

            # period_012: [時期] M月〜
            if rid == "period_012":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                return Period(start_date=f"{year}-{month:02d}-01", long_term=True, note=m.group())

            # period_rowtext_001: 時期:7月 (from Excel row_text, long term implied)
            if rid == "period_rowtext_001":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                return Period(start_date=f"{year}-{month:02d}-01", long_term=True, note=m.group())

            # period_rowtext_002: 時期:7月 (from Excel, month only)
            if rid == "period_rowtext_002":
                month = int(groups[0])
                year = now.year
                if month < now.month:
                    year += 1
                return Period(start_date=f"{year}-{month:02d}-01", note=m.group())

        return Period()

    def extract_rate(self, text: str) -> Rate:
        """単価を抽出。"""
        rules = self.library.get_rules("rate")

        for rule in rules:
            m = re.search(rule["pattern"], text, re.IGNORECASE)
            if not m:
                continue

            rid = rule["id"]
            groups = m.groups()

            # rate_001-003, 006-007: range patterns
            if rid in ("rate_001", "rate_002", "rate_003", "rate_006", "rate_007"):
                try:
                    v1 = float(groups[0].replace(",", ""))
                    v2 = float(groups[1].replace(",", ""))
                    if v1 < 1000:  # 万円単位
                        return Rate(min=v1, max=v2, unit="monthly", currency="JPY", note=m.group())
                    else:  # 円単位 → 万円換算
                        return Rate(min=round(v1 / 10000, 1), max=round(v2 / 10000, 1), unit="monthly", currency="JPY", note=m.group())
                except:  # noqa: E722
                    continue

            # rate_004: Cost range 130 K JPY/month
            if rid == "rate_004":
                try:
                    k_amount = float(groups[0].replace(",", ""))
                    return Rate(min=round(k_amount / 10, 1), max=round(k_amount / 10, 1), unit="monthly", currency="JPY", note=f"{k_amount}K JPY/月")
                except:  # noqa: E722
                    continue

            # rate_005: fixed monthly
            if rid == "rate_005":
                try:
                    v = float(groups[0])
                    if v < 1000:
                        return Rate(min=v, max=v, unit="monthly", currency="JPY", note=m.group())
                    else:
                        return Rate(min=round(v / 10000, 1), max=round(v / 10000, 1), unit="monthly", currency="JPY", note=m.group())
                except:  # noqa: E722
                    continue

        return Rate()

    def extract_project_name(self, text: str) -> str | None:
        """案件名を抽出。"""
        rules = self.library.get_rules("project_name")

        # Try rules in order
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                name = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group().strip()
                name = re.sub(r'[\s　]+', ' ', name).strip()
                if len(name) >= 3 and len(name) <= 200:
                    return name

        # Fallback: first non-empty line with meaningful content
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines:
            cleaned = re.sub(r'^[❗！!🔥①②③④⑤‼️\s]+', '', line).strip()
            if cleaned and len(cleaned) >= 5 and len(cleaned) <= 150:
                if '：' not in cleaned and ':' not in cleaned and '・' not in cleaned:
                    return cleaned[:80]

        return None

    def _extract_skill_section(self, text: str, rules: list[dict]) -> str | None:
        """スキルセクションの生テキストを抽出。"""
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                content = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group().strip()
                if len(content) >= 3:
                    return content
        return None

    def _parse_skills(self, text: str, post_cfg: dict) -> list[str]:
        """スキルテキストをパースしてリスト化。"""
        if not text:
            return []

        skills = []

        # Extract bullet points
        bullets = re.findall(r'[・—−\-]\s*([^\n]+)', text)
        if bullets:
            for b in bullets:
                b = b.strip()
                if not b:
                    continue
                # Skip headers
                if re.match(r'^(?:【|■|※|●|○)', b):
                    continue
                skills.append(b)
        else:
            # Split by delimiters
            delims = post_cfg.get("split_delimiters", ["、", "・", "/"])
            parts = re.split("|".join(delims), text)
            for p in parts:
                p = p.strip().rstrip('。．.')
                if p and len(p) >= 2:
                    skills.append(p)

        # Clean
        filtered = []
        for s in skills:
            s = s.strip()
            if not s:
                continue
            if len(s) < post_cfg.get("min_length", 2):
                continue
            if any(s.startswith(h) for h in post_cfg.get("filter_headers", [])):
                continue
            # Remove trailing qualifiers like "の方", "がある方" etc when extracting skills
            s = re.sub(r'[。．].*$', '', s)  # 句点のみで切る、読点は保持
            filtered.append(s)

        # Deduplicate
        seen = set()
        unique = []
        for s in filtered:
            key = s.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique

    def extract_skills(self, text: str) -> list[str]:
        """必須スキルを抽出。"""
        post_cfg = self.library.get_post_process("skill_requirement")
        raw = self._extract_skill_section(text, self.library.get_rules("skill_must"))
        if raw:
            return self._parse_skills(raw, post_cfg)
        # Fallback: English-style JD
        fallback = self._extract_fallback_skills(text)
        if fallback:
            return fallback
        return []

    def _extract_fallback_skills(self, text: str) -> list[str]:
        """Fallback for English-style JD / non-standard format skills."""
        skills = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^[\u2022\-\*]\s', line):
                skill = re.sub(r'^[\u2022\-\*]\s+', '', line).strip()
                if skill and len(skill) > 5 and len(skill) < 200:
                    skills.append(skill)
            elif re.match(r'^(Experience|Able|Skill|Someone|Strong|Proven|Expertise|Knowledge|Familiar)', line, re.IGNORECASE):
                if line and len(line) > 10 and len(line) < 300:
                    skills.append(line)
        return skills[:20] if skills else []

    def extract_preferred_skills(self, text: str) -> list[str]:
        """歓迎スキルを抽出。"""
        post_cfg = self.library.get_post_process("preferred_skills")
        raw = self._extract_skill_section(text, self.library.get_rules("skill_preferred"))
        if raw:
            return self._parse_skills(raw, post_cfg)
        return []

    def extract_location(self, text: str) -> Location:
        """勤務地を抽出。"""
        rules = self.library.get_rules("location")
        loc_text = None

        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                loc_text = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group().strip()
                if loc_text and len(loc_text) >= 2:
                    break

        if not loc_text:
            return Location()

        city = None
        station = None
        remote_policy = "not_specified"
        remote_detail = None

        # Extract city
        city_rules = [
            r'(東京都[一-鿿]+区)', r'(東京都)', r'(大阪[府市])', r'(千葉[県市])',
            r'(京都[府市])', r'(名古屋[市])', r'(横浜[市])', r'(神奈川[県])',
            r'(埼玉[県])', r'(兵庫[県])',
        ]
        for cr in city_rules:
            cm = re.search(cr, loc_text)
            if cm:
                city = cm.group(1)
                break
        if not city:
            if '都内' in loc_text:
                city = '東京都'
            elif '千葉' in loc_text:
                city = '千葉県'
            elif '京都' in loc_text:
                city = '京都府'
            elif '大阪' in loc_text:
                city = '大阪府'
            elif '横浜' in loc_text:
                city = '横浜市'

        # Extract station
        sm = re.search(r'([一-鿿]{1,4}(?:駅|亭))', loc_text)
        if sm:
            station = sm.group(1)

        # Remote policy
        remote_rules = self.library.get_rules("remote_policy")
        for rr in remote_rules:
            rm = re.search(rr["pattern"], loc_text)
            if not rm:
                continue
            rid = rr["id"]
            if rid == "remote_001":
                remote_policy = "full_remote"
                remote_detail = "フルリモート"
            elif rid == "remote_002":
                remote_policy = "full_remote"
                remote_detail = "基本リモート"
            elif rid in ("remote_003", "remote_004", "remote_005", "remote_006"):
                remote_policy = "hybrid"
                remote_detail = loc_text
            elif rid == "remote_007":
                remote_policy = "office_only"
                remote_detail = "基本フル出勤"

        return Location(city=city, station=station, remote_policy=remote_policy, remote_detail=remote_detail)

    def extract_headcount(self, text: str) -> int | None:
        """募集人数を抽出。"""
        rules = self.library.get_rules("headcount")
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if not m:
                continue
            rid = rule["id"]
            if rid == "head_006":
                return None  # 複数名 is ambiguous
            if rid == "head_004":
                # Range pattern: take max
                try:
                    return int(m.group(1))
                except:  # noqa: E722
                    continue
            try:
                v = int(m.group(1)) if m.lastindex and m.lastindex >= 1 else int(m.group())
                if 1 <= v <= 100:
                    return v
            except:  # noqa: E722
                continue
        return None

    def extract_interviews(self, text: str) -> int | None:
        """面接回数を抽出。"""
        rules = self.library.get_rules("interviews")
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                try:
                    v = int(m.group(1)) if m.lastindex and m.lastindex >= 1 else int(m.group())
                    if 1 <= v <= 10:
                        return v
                except:  # noqa: E722
                    continue
        return None

    def extract_japanese_level(self, text: str) -> JapaneseLevelInfo:
        """日本語レベルを抽出。"""
        rules = self.library.get_rules("japanese_level")
        matched = []
        for rule in rules:
            m = re.search(rule["pattern"], text, re.IGNORECASE)
            if m:
                rid = rule["id"]
                matched.append(rid)
                if m.lastindex and m.lastindex >= 1:
                    matched.append(m.group(1))

        if not matched:
            return JapaneseLevelInfo()

        # Determine the highest level found
        level = "not_specified"
        level_jp = None

        # Check text directly for N1/N2 level mentions
        n_direct = re.search(r'(?:^|[^\w])[Nn]([1-4])(?:\s*流暢|\s*以上|$|[^\w])', text)
        if n_direct and 'n_direct' not in str(matched):
            matched.append(f'n{n_direct.group(1)}')

        # Rule ID → level mapping (for rules that don't capture a level value)
        rule_id_levels = {
            "jp_003": ("business", "日本語必須"),
            "jp_005": ("business", "ビジネスレベル"),
            "jp_006": ("business", "日本語流暢"),
            "jp_007": ("business", "Japanese only OK"),
            "jp_008": ("business", "外国籍可"),
            "jp_009": ("business", "業務レベル"),
        }

        for item in matched:
            item_str = str(item)
            item_lower = item_str.lower()

            # Check rule ID first
            if item_str in rule_id_levels:
                mapped_level, mapped_jp = rule_id_levels[item_str]
                if level in ("not_specified",) or level == "business":
                    level = mapped_level
                    level_jp = mapped_jp
                continue

            # Detect N1/N2 level from direct text match
            if re.match(r'^n[12]$', item_lower):
                if level in ('not_specified',):
                    level = 'business'
                    level_jp = item_str
            if re.search(r'native|ネイティブ|母国語', item_str):
                level = "native"
                level_jp = "ネイティブ"
            elif re.search(r'n[12]流暢|n[12]', item_str):
                level = "business"
                level_jp = item_str
            elif re.search(r'n[34]', item_str):
                level_val = item_str
                if level_val.lower() == "n3":
                    level = "n3"
                elif level_val.lower() == "n4":
                    level = "n4"
                level_jp = item_str
            elif re.search(r'business|ビジネス|流暢', item_str):
                if level in ("not_specified",):
                    level = "business"
            elif re.search(r'業務水平|コミュニケーション', item_str):
                if level in ("not_specified",):
                    level = "business"
            elif re.search(r'外国籍.*可', item_str):
                if level in ("not_specified",):
                    level = "business"

        return JapaneseLevelInfo(level=level, level_jp=level_jp)

    def extract_english_level(self, text: str) -> EnglishLevelInfo:
        """英語レベルを抽出。"""
        rules = self.library.get_rules("english_level")
        for rule in rules:
            m = re.search(rule["pattern"], text, re.IGNORECASE)
            if m:
                rid = rule["id"]
                if rid == "eng_001":
                    return EnglishLevelInfo(level="business", detail="読み書き可能")
                elif rid == "eng_002":
                    return EnglishLevelInfo(level="daily", detail="日常会話可能")
                elif rid == "eng_003":
                    return EnglishLevelInfo(level="business", detail=m.group())
        return EnglishLevelInfo()

    def extract_industry(self, text: str) -> str | None:
        """業種を抽出。"""
        rules = self.library.get_rules("industry")
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                return m.group().strip()
        # Check if SAP-related context
        if re.search(r'SAP|Oracle\s*Fusion', text, re.IGNORECASE):
            if '製造' in text:
                return '製造'
            if '製薬' in text:
                return '製薬'
            if 'エネルギー' in text:
                return 'エネルギー'
            if '電気機器' in text:
                return '電気機器'
            return 'SAP/ERP'
        return None

    def extract_trade_flow(self, text: str) -> TradeFlow:
        """商流を抽出。"""
        rules = self.library.get_rules("trade_flow")
        tf = TradeFlow()
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if not m:
                continue
            rid = rule["id"]
            if rid == "trade_001":
                tf.contract_type = "jun_inin"
                tf.contract_type_jp = "準委任"
            elif rid == "trade_002":
                tf.contract_type = "jun_inin"
                tf.contract_type_jp = "派遣または準委任"
            elif rid == "trade_003":
                tf.contract_type = "haken"
                tf.contract_type_jp = "派遣"
            elif rid == "trade_004":
                tf.contract_type = "ukeoi"
                tf.contract_type_jp = "請負"
            elif rid == "trade_005":
                tf.contract_type = "ses"
                tf.contract_type_jp = "SES"
            elif rid == "trade_006":
                tf.contract_type_jp = m.group(1).strip()
            elif rid == "trade_007":
                val = m.group(1).strip()
                if "貴社" in val or "自社" in val:
                    tf.layers = 1
            elif rid == "trade_008":
                tf.layers = 1
        return tf

    def extract_experience_years(self, text: str) -> dict | None:
        """経験年数を抽出。"""
        rules = self.library.get_rules("experience_years")
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                try:
                    y = int(m.group(1))
                    return {"min": y, "description": m.group().strip()}
                except:  # noqa: E722
                    continue
        return None

    def extract_immediate_start(self, text: str) -> bool | None:
        """即日参画可否。"""
        rules = self.library.get_rules("immediate_start")
        for rule in rules:
            if re.search(rule["pattern"], text):
                return True
        return None

    def extract_remarks(self, text: str) -> str | None:
        """備考を抽出。"""
        rules = self.library.get_rules("remarks")
        for rule in rules:
            m = re.search(rule["pattern"], text)
            if m:
                val = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group().strip()
                if len(val) >= 5:
                    return val[:2000]
        return None


# ═══════════════════════════════════════════
# ファイルプロセッサ
# ═══════════════════════════════════════════

class CaseProcessor:
    """案件ファイルを処理してケースリストを生成。"""

    def __init__(self, engine: RuleEngine):
        self.engine = engine
        self.normalizer = JapaneseTextNormalizer()

    def _build_case(self, text: str, fmt: str, filename: str) -> RecruitmentCase:
        """テキストから案件を構築。"""
        period = self.engine.extract_period(text)
        # 即日かつ期間未設定の場合
        immediate = self.engine.extract_immediate_start(text)
        if immediate and not period.start_date:
            period.start_date = datetime.now().strftime("%Y-%m-%d")

        return RecruitmentCase(
            project_name=self.engine.extract_project_name(text),
            project_description=None,
            skill_requirement=self.engine.extract_skills(text),
            preferred_skills=self.engine.extract_preferred_skills(text),
            experience_years=self.engine.extract_experience_years(text),
            location=self.engine.extract_location(text),
            rate=self.engine.extract_rate(text),
            period=period,
            headcount=self.engine.extract_headcount(text),
            industry=self.engine.extract_industry(text),
            trade_flow=self.engine.extract_trade_flow(text),
            japanese_level=self.engine.extract_japanese_level(text),
            english_level=self.engine.extract_english_level(text),
            interviews=self.engine.extract_interviews(text),
            immediate_start=immediate,
            remarks=self.engine.extract_remarks(text),
            original_text=text[:30000],
            source=SourceInfo(original_format=fmt, filename=filename),
        )

    def process_txt(self, file_path: Path) -> list[RecruitmentCase]:
        """単一テキストファイルを処理。"""
        text = file_path.read_text(encoding="utf-8")
        text = self.normalizer.normalize(text, preserve_newlines=True)
        return [self._build_case(text, "text", file_path.name)]

    def process_markdown(self, file_path: Path) -> list[RecruitmentCase]:
        """マークダウン（複数案件）を処理。"""
        text = self.normalizer.normalize(file_path.read_text(encoding="utf-8"), preserve_newlines=True)
        lines = text.split('\n')

        # Detect case boundaries
        case_markers = r'^(?:案件名[\s\u3000]*[：:]|■\s*案件名|[！!🔥]\s*\S|①②③④⑤|直接客户|Need candidates|募集[：:]|■期間)'
        sections = []
        current = []

        for line in lines:
            if re.match(case_markers, line.strip()):
                sections.append('\n'.join(current))
                current = [line]
            elif line.strip().startswith('----') and current:
                sections.append('\n'.join(current))
                current = []
            else:
                current.append(line)

        if current:
            sections.append('\n'.join(current))

        sections = [s.strip() for s in sections if len(s.strip()) > 50]

        cases = []
        for section in sections:
            if section.replace('-', '').strip() == '':
                continue
            case = self._build_case(section, "text", file_path.name)
            if case.project_name:
                cases.append(case)

        return cases

    def process_excel(self, file_path: Path) -> list[RecruitmentCase]:
        """Excel案件一覧を処理。"""
        try:
            import openpyxl
        except ImportError:
            print("  ⚠ openpyxl not installed, skipping Excel processing")
            return []

        wb = openpyxl.load_workbook(str(file_path))
        ws = wb.active
        cases = []

        for row in ws.iter_rows(min_row=2, values_only=True):
            vals = [str(c) if c else "" for c in row]
            # First 8 columns are data; column 9+ is formula, skip
            no = vals[0] if len(vals) > 0 else ""
            period_str = vals[1] if len(vals) > 1 else ""
            headcount_str = vals[2] if len(vals) > 2 else ""
            project_name = vals[3] if len(vals) > 3 else ""
            role = vals[4] if len(vals) > 4 else ""
            level = vals[5] if len(vals) > 5 else ""
            skill_text = vals[6] if len(vals) > 6 else ""
            location_text = vals[7] if len(vals) > 7 else ""

            if not project_name.strip() or project_name.strip() == "None":
                continue

            row_text = (f"案件名:{project_name}\n時期:{period_str}\n人数:{headcount_str}\n"
                       f"役割:{role}\nレベル:{level}\n【必須】\n{skill_text}\n場所:{location_text}")
            # Don't normalize row_text - keep newlines for rule matching

            case = self._build_case(row_text, "excel", file_path.name)
            if not case.project_name:
                case.project_name = project_name.strip()[:100] or f"SAP案件{no}"
            if case.headcount is None and headcount_str:
                m = re.search(r'(\d+)', headcount_str)
                if m:
                    case.headcount = int(m.group(1))
            cases.append(case)

        wb.close()
        return cases


# ═══════════════════════════════════════════
# メイン実行
# ═══════════════════════════════════════════

def main():
    data_dir = Path(__file__).parent.parent / "data"
    output_dir = data_dir / "output"
    rules_path = data_dir / "rules" / "field_rules.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ルールエンジン初期化
    if not rules_path.exists():
        print(f"[ERROR] ルールファイルが見つかりません: {rules_path}")
        sys.exit(1)

    engine = RuleEngine(str(rules_path))
    processor = CaseProcessor(engine)

    print(f"📚 ルールライブラリ: {rules_path.name}")
    rule_count = sum(len(v) for v in engine.library.rules.values())
    print(f"   全ルール数: {rule_count}")

    files_to_process = [
        ("案件1.txt", "text", processor.process_txt),
        ("案件List.md", "text", processor.process_markdown),
        ("7月SAP案件一覧_0610.xlsx", "excel", processor.process_excel),
    ]

    all_results = {}
    stats = {"total_cases": 0, "files_processed": 0, "extraction_mode": "rule_based"}

    for filename, fmt, process_fn in files_to_process:
        file_path = data_dir / filename
        if not file_path.exists():
            print(f"\n  ⚠ スキップ: {filename} (not found)")
            continue

        print(f"\n{'='*60}")
        print(f"📄 処理中: {filename}")
        print(f"{'='*60}")

        try:
            cases = process_fn(file_path)
            all_results[filename] = {
                "file": filename, "format": fmt, "case_count": len(cases),
                "cases": [c.model_dump(exclude_none=True) for c in cases],
            }
            stats["total_cases"] += len(cases)
            stats["files_processed"] += 1

            print(f"   ✓ 抽出完了: {len(cases)} 件の案件")
            for i, case in enumerate(cases):
                sk = ", ".join(case.skill_requirement[:3]) if case.skill_requirement else "-"
                if len(case.skill_requirement) > 3:
                    sk += f" (+{len(case.skill_requirement)-3})"
                loc = case.location.city or "?"
                rate = f"{case.rate.min}~{case.rate.max}" if case.rate.min else "-"
                period = str(case.period.start_date or "?")[:10]
                imm = " 即日OK" if case.immediate_start else ""
                jl = f" JP:{case.japanese_level.level}" if case.japanese_level.level != "not_specified" else ""
                print(f"     [{i+1}] {case.project_name[:50] or '(名称なし)'}")
                print(f"         場所:{loc} | 単価:{rate}万円/月 | {len(case.skill_requirement)}スキル | {period}{imm}{jl}")

        except Exception as e:
            import traceback
            print(f"   ✗ エラー: {e}")
            traceback.print_exc()
            all_results[filename] = {"file": filename, "format": fmt, "error": str(e)}

    # 出力JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    class DateEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super().default(obj)

    output = {
        "extraction_date": datetime.now().isoformat(),
        "rule_library": {"path": str(rules_path), "total_rules": rule_count},
        "stats": stats,
        "results": all_results,
    }

    json_path = output_dir / f"extraction_result_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, cls=DateEncoder)

    print(f"\n{'='*60}")
    print(f"✅ ルール抽出完了")
    print(f"   処理ファイル数: {stats['files_processed']}")
    print(f"   全案件数: {stats['total_cases']}")
    print(f"   使用ルール数: {rule_count}")
    print(f"   結果保存先: {json_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
