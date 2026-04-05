"""
Cyber collector — CVEs from NVD API v2, CISA KEV, and HaveIBeenPwned breach signals.
"""
from datetime import datetime, timedelta, timezone
from typing import List
import requests

from collectors.base import BaseCollector
from models.intel_item import IntelItem, Domain, Severity
from utils.config_loader import get_config, get_secret


class CyberCollector(BaseCollector):
    name = "cyber"

    def collect(self) -> List[IntelItem]:
        cfg = get_config()["collectors"]["cyber"]
        items = []
        items.extend(self._collect_nvd(cfg["nvd"]))
        if cfg["cisa_kev"]["enabled"]:
            items.extend(self._collect_cisa_kev())
        if cfg["hibp"]["enabled"]:
            items.extend(self._collect_hibp(cfg["hibp"].get("monitor_domains", [])))
        return items

    def _collect_nvd(self, cfg: dict) -> List[IntelItem]:
        items = []
        days_back = cfg.get("days_back", 1)
        min_cvss = cfg.get("min_cvss_score", 7.0)
        max_results = cfg.get("max_results", 10)

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)
        pub_start = start.strftime("%Y-%m-%dT%H:%M:%S.000")
        pub_end = end.strftime("%Y-%m-%dT%H:%M:%S.000")

        headers = {}
        nvd_key = get_secret("NVD_API_KEY")
        if nvd_key:
            headers["apiKey"] = nvd_key

        try:
            url = (
                f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                f"?pubStartDate={pub_start}&pubEndDate={pub_end}"
                f"&cvssV3Severity=HIGH,CRITICAL"
                f"&resultsPerPage={max_results}"
            )
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            for vuln in data.get("vulnerabilities", []):
                cve = vuln.get("cve", {})
                cve_id = cve.get("id", "UNKNOWN")
                descriptions = cve.get("descriptions", [])
                desc = next((d["value"] for d in descriptions if d["lang"] == "en"), "No description available.")

                # Get CVSS score
                metrics = cve.get("metrics", {})
                cvss_score = None
                for version in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                    if version in metrics and metrics[version]:
                        cvss_score = metrics[version][0].get("cvssData", {}).get("baseScore")
                        break

                if cvss_score is not None and cvss_score < min_cvss:
                    continue

                severity = Severity.CRITICAL if (cvss_score or 0) >= 9.0 else Severity.HIGH

                pub_date_str = cve.get("published", "")
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except Exception:
                    pub_date = datetime.utcnow()

                items.append(IntelItem(
                    domain=Domain.CYBER,
                    source="NVD",
                    title=f"{cve_id} — CVSS {cvss_score or 'N/A'}: {desc[:80]}...",
                    summary=desc[:500],
                    url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    published_at=pub_date,
                    severity=severity,
                    tags=[cve_id, "CVE", "vulnerability"],
                    confidence=1.0,
                ))
        except Exception as e:
            print(f"[cyber] NVD error: {e}")
        return items

    def _collect_cisa_kev(self) -> List[IntelItem]:
        items = []
        try:
            url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            vulns = data.get("vulnerabilities", [])

            # Only show KEV entries added in the last 3 days
            cutoff = datetime.utcnow() - timedelta(days=3)
            recent = [
                v for v in vulns
                if datetime.strptime(v.get("dateAdded", "2000-01-01"), "%Y-%m-%d") > cutoff
            ]

            for v in recent[:5]:
                cve_id = v.get("cveID", "UNKNOWN")
                vendor = v.get("vendorProject", "Unknown Vendor")
                product = v.get("product", "Unknown Product")
                desc = v.get("shortDescription", "No description.")
                due_date = v.get("dueDate", "N/A")
                items.append(IntelItem(
                    domain=Domain.CYBER,
                    source="CISA KEV",
                    title=f"CISA KEV: {cve_id} — {vendor} {product}",
                    summary=f"{desc} Federal agencies required to patch by {due_date}.",
                    url=f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                    published_at=datetime.utcnow(),
                    severity=Severity.CRITICAL,
                    tags=[cve_id, "KEV", "CISA", vendor.lower(), "actively exploited"],
                    confidence=1.0,
                ))
        except Exception as e:
            print(f"[cyber] CISA KEV error: {e}")
        return items

    def _collect_hibp(self, monitor_domains: list) -> List[IntelItem]:
        """Check for recent public breaches via HIBP. Domain monitoring requires paid key."""
        items = []
        hibp_key = get_secret("HIBP_API_KEY")
        if not hibp_key:
            return items

        try:
            # Fetch latest public breaches
            resp = requests.get(
                "https://haveibeenpwned.com/api/v3/latestbreach",
                headers={"hibp-api-key": hibp_key, "user-agent": "daily-intel/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            breach = resp.json()
            items.append(IntelItem(
                domain=Domain.CYBER,
                source="HaveIBeenPwned",
                title=f"Latest Breach: {breach.get('Name', 'Unknown')} — {breach.get('PwnCount', 0):,} accounts",
                summary=(
                    f"{breach.get('Name')} breach exposed {breach.get('PwnCount', 0):,} accounts. "
                    f"Data types: {', '.join(breach.get('DataClasses', [])[:5])}."
                ),
                url=f"https://haveibeenpwned.com/PwnedWebsites#{ breach.get('Name', '')}",
                published_at=datetime.utcnow(),
                severity=Severity.HIGH,
                tags=["breach", "HIBP", "credentials", breach.get("Name", "").lower()],
                confidence=1.0,
            ))
        except Exception as e:
            print(f"[cyber] HIBP error: {e}")
        return items
