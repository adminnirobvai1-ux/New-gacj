import os
XHAWON_VERSION = "v12.0-ENTERPRISE-READY"

# ============================================================
# ⚠️ আপনার তথ্য এখানে বসান - শুধু এই ২টি লাইন পরিবর্তন করুন
# ============================================================
BOT_TOKEN = "8932852728:AAHvJeyMl-dtO2IJ1eRx2xeRSRSVRLzzySU"  # ← @BotFather থেকে নিন
GEMINI_API_KEY = "AQ.Ab8RN6JxPLKTHIbx_BPo86x9JA8mNxF_t_eLHPkGKMUn1VerVQ"  # ← Google AI Studio থেকে নিন
ADMIN_CHAT_ID = "8746661403"  # ← @userinfobot থেকে নিন (ঐচ্ছিক)
# ============================================================

# যদি Wispbyte Environment Variable ব্যবহার করতে চান, তাহলে উপরের লাইনগুলো ফাঁকা রেখে দিন
# এবং Wispbyte ড্যাশবোর্ডে BOT_TOKEN, GEMINI_API_KEY, ADMIN_CHAT_ID সেট করুন

import io, json, base64, sqlite3, hashlib, asyncio, zipfile, math, random
from pathlib import Path
from datetime import datetime, timedelta, timezone
from threading import RLock
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import numpy as np

# ============================================================
# ENVIRONMENT VARIABLES (Wispbyte support)
# ============================================================
# Environment variable গুলোকে priority দিন
BOT_TOKEN = os.getenv("BOT_TOKEN", BOT_TOKEN).strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY).strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", ADMIN_CHAT_ID).strip()

if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError(
        '❌ BOT_TOKEN সেট করা হয়নি!\n'
        'Wispbyte Environment Variables-এ BOT_TOKEN বসান অথবা\n'
        'কোডের ১৪ নম্বর লাইনে YOUR_BOT_TOKEN_HERE এর জায়গায় আপনার টোকেন বসান।'
    )

if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("⚠️ GEMINI_API_KEY সেট করা হয়নি। Gemini AI ফিচার কাজ করবে না।")

# ============================================================
# GOOGLE GEMINI AI IMPORT
# ============================================================
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
    print("✅ Google Gemini AI loaded")
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google Gemini AI not available. Install: pip install google-genai")

# ============================================================
# ADVANCED ML IMPORTS
# ============================================================
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
    print("✅ Scikit-learn loaded")
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ Scikit-learn not available")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    PYTORCH_AVAILABLE = True
    print("✅ PyTorch loaded")
except ImportError:
    PYTORCH_AVAILABLE = False
    print("⚠️ PyTorch not available")

import aiohttp
from cryptography.fernet import Fernet
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================================
# CONFIGURATION
# ============================================================
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
DB_PATH = "xhawon_data.db"
BACKUP_DIR = "backups"
KEY_FILE = "encryption.key"
API_TIMEOUT = 15
POLL_INTERVAL = 4
LEARNING_POLL = 8
REPORT_HOURS = 24

# Learning Parameters
MIN_SAMPLES = 30
MIN_RECENT = 15
MIN_VALIDATION = 25
QUALIFY_RATE = 55.0
QUALIFY_VALIDATION = 55.0
RECENT_FLOOR = 50.0
DECAY_GAP = 20.0
SIGNIFICANCE_Z = 1.645

REAL_TIME_CHECK_INTERVAL = 180

print("=" * 60)
print(f"🚀 XHAWON {XHAWON_VERSION}")
print("=" * 60)
print(f"✅ BOT_TOKEN: {'✅ Set' if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ Missing'}")
print(f"✅ GEMINI_API_KEY: {'✅ Set' if GEMINI_API_KEY and GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE' else '❌ Missing'}")
print(f"✅ ADMIN_CHAT_ID: {'✅ Set' if ADMIN_CHAT_ID and ADMIN_CHAT_ID != 'YOUR_CHAT_ID_HERE' else '⚠️ Optional'}")
print("=" * 60)


# ============================================================
# 1. USER PROFILING SYSTEM
# ============================================================

@dataclass
class UserProfile:
    user_id: int
    username: str
    join_date: datetime
    experience_level: str
    risk_tolerance: str
    preferred_patterns: List[str]
    successful_trades: int
    failed_trades: int
    total_profit: float
    average_confidence: float
    favorite_time: int
    learning_progress: float
    achievements: List[str]
    last_active: datetime
    strategy_preference: str
    weekly_performance: List[float]
    monthly_performance: List[float]
    pattern_history: List[str]
    skill_scores: Dict[str, float]
    personalized_threshold: float


class UserProfiler:
    def __init__(self, db):
        self.db = db
        self.profiles = {}
        self.skill_categories = [
            'pattern_recognition', 'risk_management', 
            'timing_accuracy', 'strategy_selection', 'emotional_control'
        ]
        self.experience_levels = {
            'BEGINNER': {'min_trades': 0, 'threshold': 45},
            'INTERMEDIATE': {'min_trades': 50, 'threshold': 55},
            'ADVANCED': {'min_trades': 200, 'threshold': 62},
            'EXPERT': {'min_trades': 500, 'threshold': 70}
        }
        self._init_profiles()
    
    def _init_profiles(self):
        try:
            self.db.c.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                join_date TEXT,
                experience_level TEXT,
                risk_tolerance TEXT,
                preferred_patterns TEXT,
                successful_trades INTEGER,
                failed_trades INTEGER,
                total_profit REAL,
                average_confidence REAL,
                favorite_time INTEGER,
                learning_progress REAL,
                achievements TEXT,
                last_active TEXT,
                strategy_preference TEXT,
                weekly_performance TEXT,
                monthly_performance TEXT,
                pattern_history TEXT,
                skill_scores TEXT,
                personalized_threshold REAL
            )
            """)
            self.db.c.commit()
        except Exception as e:
            print(f"Profile init error: {e}")
    
    def load_profile(self, user_id: int) -> UserProfile:
        if user_id in self.profiles:
            return self.profiles[user_id]
        
        try:
            row = self.db.c.execute(
                "SELECT * FROM user_profiles WHERE user_id=?", (user_id,)
            ).fetchone()
            
            if row:
                profile = UserProfile(
                    user_id=row['user_id'],
                    username=row['username'],
                    join_date=datetime.fromisoformat(row['join_date']),
                    experience_level=row['experience_level'],
                    risk_tolerance=row['risk_tolerance'],
                    preferred_patterns=json.loads(row['preferred_patterns']),
                    successful_trades=row['successful_trades'],
                    failed_trades=row['failed_trades'],
                    total_profit=row['total_profit'],
                    average_confidence=row['average_confidence'],
                    favorite_time=row['favorite_time'],
                    learning_progress=row['learning_progress'],
                    achievements=json.loads(row['achievements']),
                    last_active=datetime.fromisoformat(row['last_active']),
                    strategy_preference=row['strategy_preference'],
                    weekly_performance=json.loads(row['weekly_performance']),
                    monthly_performance=json.loads(row['monthly_performance']),
                    pattern_history=json.loads(row['pattern_history']),
                    skill_scores=json.loads(row['skill_scores']),
                    personalized_threshold=row['personalized_threshold']
                )
                self.profiles[user_id] = profile
                return profile
        except Exception as e:
            print(f"Load profile error: {e}")
        
        profile = self._create_default_profile(user_id)
        self.profiles[user_id] = profile
        self._save_profile(profile)
        return profile
    
    def _create_default_profile(self, user_id: int) -> UserProfile:
        return UserProfile(
            user_id=user_id,
            username="Unknown",
            join_date=datetime.now(),
            experience_level="BEGINNER",
            risk_tolerance="MEDIUM",
            preferred_patterns=[],
            successful_trades=0,
            failed_trades=0,
            total_profit=0.0,
            average_confidence=0.5,
            favorite_time=datetime.now().hour,
            learning_progress=0.0,
            achievements=[],
            last_active=datetime.now(),
            strategy_preference="MODERATE",
            weekly_performance=[],
            monthly_performance=[],
            pattern_history=[],
            skill_scores={skill: 0.0 for skill in self.skill_categories},
            personalized_threshold=50.0
        )
    
    def _save_profile(self, profile: UserProfile):
        try:
            self.db.c.execute("""
            INSERT OR REPLACE INTO user_profiles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                profile.user_id, profile.username,
                profile.join_date.isoformat(),
                profile.experience_level,
                profile.risk_tolerance,
                json.dumps(profile.preferred_patterns),
                profile.successful_trades,
                profile.failed_trades,
                profile.total_profit,
                profile.average_confidence,
                profile.favorite_time,
                profile.learning_progress,
                json.dumps(profile.achievements),
                profile.last_active.isoformat(),
                profile.strategy_preference,
                json.dumps(profile.weekly_performance),
                json.dumps(profile.monthly_performance),
                json.dumps(profile.pattern_history),
                json.dumps(profile.skill_scores),
                profile.personalized_threshold
            ))
            self.db.c.commit()
        except Exception as e:
            print(f"Save profile error: {e}")
    
    def update_profile(self, user_id: int, data: Dict):
        profile = self.load_profile(user_id)
        
        if 'username' in data:
            profile.username = data['username']
        if 'successful_trades' in data:
            profile.successful_trades += data['successful_trades']
        if 'failed_trades' in data:
            profile.failed_trades += data['failed_trades']
        if 'profit' in data:
            profile.total_profit += data['profit']
        if 'confidence' in data:
            profile.average_confidence = (profile.average_confidence * 0.7 + data['confidence'] * 0.3)
        
        profile.last_active = datetime.now()
        profile.learning_progress = self._calculate_learning_progress(profile)
        profile.experience_level = self._determine_experience_level(profile)
        profile.personalized_threshold = self._calculate_personalized_threshold(profile)
        
        self._save_profile(profile)
        return profile
    
    def _calculate_learning_progress(self, profile: UserProfile) -> float:
        total_trades = profile.successful_trades + profile.failed_trades
        if total_trades == 0:
            return 0.0
        progress = min(100, (total_trades / 1000) * 100)
        success_rate = profile.successful_trades / total_trades if total_trades > 0 else 0
        progress += success_rate * 20
        avg_skill = sum(profile.skill_scores.values()) / len(profile.skill_scores)
        progress += avg_skill * 0.2
        return min(100, progress)
    
    def _determine_experience_level(self, profile: UserProfile) -> str:
        total_trades = profile.successful_trades + profile.failed_trades
        for level, criteria in self.experience_levels.items():
            if total_trades >= criteria['min_trades']:
                success_rate = (profile.successful_trades / total_trades * 100) if total_trades > 0 else 0
                if success_rate >= criteria['threshold']:
                    return level
        return "BEGINNER"
    
    def _calculate_personalized_threshold(self, profile: UserProfile) -> float:
        base = 50.0
        if profile.experience_level == "BEGINNER":
            base += 5
        elif profile.experience_level == "INTERMEDIATE":
            base += 0
        elif profile.experience_level == "ADVANCED":
            base -= 5
        elif profile.experience_level == "EXPERT":
            base -= 10
        
        if profile.risk_tolerance == "LOW":
            base += 10
        elif profile.risk_tolerance == "HIGH":
            base -= 5
        
        avg_skill = sum(profile.skill_scores.values()) / len(profile.skill_scores)
        base -= (avg_skill - 50) * 0.2
        return max(30, min(80, base))
    
    def get_personalized_patterns(self, user_id: int, patterns: List[Dict]) -> List[Dict]:
        profile = self.load_profile(user_id)
        if not patterns:
            return []
        
        scored_patterns = []
        for p in patterns:
            score = p.get('score', 0)
            
            if profile.experience_level == "BEGINNER":
                if p.get('type') in ['SEQUENCE', 'TIME_SPECIFIC']:
                    score += 10
            elif profile.experience_level == "ADVANCED":
                if p.get('type') in ['COMPOSITE', 'ENSEMBLE']:
                    score += 10
            
            if profile.risk_tolerance == "LOW":
                score += p.get('confidence', 0) * 0.5
            elif profile.risk_tolerance == "HIGH":
                score += p.get('rate', 0) * 0.3
            
            scored_patterns.append((p, score))
        
        scored_patterns.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in scored_patterns]
    
    def generate_user_insights(self, user_id: int) -> str:
        profile = self.load_profile(user_id)
        
        lines = [
            "👤 **YOUR PERSONALIZED PROFILE**",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 Level: {profile.experience_level}",
            f"🎯 Risk Tolerance: {profile.risk_tolerance}",
            f"📈 Success Rate: {(profile.successful_trades / (profile.successful_trades + profile.failed_trades + 1) * 100):.1f}%",
            f"🏆 Trades: {profile.successful_trades + profile.failed_trades}",
            f"💰 Profit: {profile.total_profit:.2f}",
            "",
            "📊 SKILL SCORES:",
        ]
        
        for skill, score in profile.skill_scores.items():
            bar = "█" * int(score / 10) + "░" * (10 - int(score / 10))
            lines.append(f"   • {skill.replace('_', ' ').title()}: {bar} {score:.0f}%")
        
        lines += [
            "",
            f"🎯 Learning Progress: {profile.learning_progress:.1f}%",
            f"🎯 Personalized Threshold: {profile.personalized_threshold:.1f}%",
            "",
            "🏅 ACHIEVEMENTS:",
        ]
        
        if profile.achievements:
            for ach in profile.achievements:
                lines.append(f"   ✅ {ach}")
        else:
            lines.append("   🔒 No achievements yet. Keep learning!")
        
        return "\n".join(lines)


# ============================================================
# 2. GEMINI AI INTEGRATION
# ============================================================

class GeminiAIAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.is_available = False
        self.analysis_cache = {}
        self._init_client()
    
    def _init_client(self):
        if not GEMINI_AVAILABLE:
            print("⚠️ Gemini AI not available")
            return
        
        try:
            if self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE":
                os.environ["GOOGLE_API_KEY"] = self.api_key
                self.client = genai.Client()
                self.is_available = True
                print("✅ Gemini AI client initialized")
            else:
                print("⚠️ Gemini API Key not set")
        except Exception as e:
            print(f"❌ Gemini AI initialization error: {e}")
            self.is_available = False
    
    async def analyze_patterns(self, patterns: List[Dict], data: List[Dict]) -> Dict:
        if not self.is_available or not patterns:
            return {'error': 'Gemini AI not available'}
        
        try:
            top_patterns = patterns[:10] if len(patterns) >= 10 else patterns
            recent_data = data[-30:] if len(data) >= 30 else data
            
            patterns_text = ""
            for i, p in enumerate(top_patterns[:10], 1):
                patterns_text += f"""
                Pattern {i}:
                - Type: {p.get('type', 'Unknown')}
                - Pattern: {p.get('pattern', 'N/A')}
                - Success Rate: {p.get('rate', 0):.1f}%
                - Confidence: {p.get('confidence', 'LOW')}
                - Status: {p.get('status', 'REVIEW')}
                """
            
            data_text = ", ".join([str(d.get('n', '?')) for d in recent_data])
            
            prompt = f"""
            You are a professional market analyst. Analyze these patterns:

            RECENT DATA: [{data_text}]

            PATTERNS:
            {patterns_text}

            Provide:
            1. Quality assessment
            2. Market trends
            3. Risk analysis
            4. Actionable recommendations
            """
            
            response = await self._call_gemini(prompt)
            
            if response:
                return {
                    'success': True,
                    'analysis': response,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': 'No response from Gemini'}
                
        except Exception as e:
            print(f"Gemini analysis error: {e}")
            return {'error': str(e)}
    
    async def _call_gemini(self, prompt: str) -> Optional[str]:
        if not self.is_available or not self.client:
            return None
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.0-flash-exp",
                contents=prompt
            )
            
            if response and hasattr(response, 'text'):
                return response.text
            return None
            
        except Exception as e:
            print(f"Gemini API call error: {e}")
            return None


# ============================================================
# 3. CORE LEARNER
# ============================================================

class UltimateLearner:
    def __init__(self, db):
        self.db = db
        self.gemini = GeminiAIAnalyzer(GEMINI_API_KEY)
        self.profiler = UserProfiler(db)
        self.pattern_memory = []
        self.qualified_patterns = []
        self.gemini_analysis_cache = {}
        self.performance_metrics = {
            'accuracy': [],
            'confidence': [],
            'pattern_quality': []
        }
    
    @staticmethod
    def bs(n):
        return "BIG" if n >= 5 else "SMALL"
    
    @staticmethod
    def pct(a, b):
        return round(a * 100 / b, 2) if b else 0.0
    
    def rows(self):
        out = []
        for r in self.db.all_results():
            try:
                issue = str(r.get("issue", "")).strip()
                n = int(r["number"])
                if not issue or not 0 <= n <= 9:
                    continue
                raw = r.get("timestamp")
                try:
                    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    dt = datetime.now()
                out.append({"issue": issue, "n": n, "dt": dt, "bs": self.bs(n)})
            except Exception:
                pass
        if out and all(x["issue"].isdigit() for x in out):
            out.sort(key=lambda x: int(x["issue"]))
        else:
            out.sort(key=lambda x: x["dt"])
        return out
    
    def _evaluate_pattern(self, key: str, pattern_type: str, seq: tuple, 
                          targets: List[Tuple]) -> Optional[Dict]:
        if len(targets) < MIN_SAMPLES:
            return None
        
        vals = [x[0] for x in targets]
        times = [x[1] for x in targets]
        
        n = len(vals)
        train_end = int(n * 0.7)
        valid_end = int(n * 0.85)
        
        train = vals[:train_end]
        valid = vals[train_end:valid_end]
        hold = vals[valid_end:]
        
        if len(train) < 15 or len(valid) < MIN_VALIDATION or len(hold) < MIN_VALIDATION:
            return None
        
        target = Counter(train).most_common(1)[0][0]
        
        hist_rate = self.pct(sum(v == target for v in vals), n)
        valid_rate = self.pct(sum(v == target for v in valid), len(valid))
        hold_rate = self.pct(sum(v == target for v in hold), len(hold))
        recent = vals[-min(MIN_RECENT, n):]
        recent_rate = self.pct(sum(v == target for v in recent), len(recent))
        
        stability = 100 - abs(hist_rate - recent_rate) - abs(valid_rate - hold_rate)
        score = hist_rate * 0.15 + valid_rate * 0.20 + hold_rate * 0.25 + recent_rate * 0.15 + stability * 0.15
        
        if hold_rate >= QUALIFY_VALIDATION and valid_rate >= QUALIFY_VALIDATION and recent_rate >= RECENT_FLOOR:
            status = "QUALIFIED"
        elif hold_rate < 45 and valid_rate < 45:
            status = "REJECTED"
        elif hist_rate >= QUALIFY_RATE and recent_rate < RECENT_FLOOR:
            status = "DECAYING"
        else:
            status = "REVIEW"
        
        return {
            'key': key,
            'type': pattern_type,
            'pattern': f"{' → '.join(map(str, seq))} → {target}",
            'target': target,
            'n': n,
            'correct': sum(v == target for v in vals),
            'wrong': sum(v != target for v in vals),
            'rate': hist_rate,
            'recent_n': len(recent),
            'recent_correct': sum(v == target for v in recent),
            'recent_rate': recent_rate,
            'validation_n': len(valid),
            'validation_correct': sum(v == target for v in valid),
            'validation_rate': valid_rate,
            'holdout_n': len(hold),
            'holdout_correct': sum(v == target for v in hold),
            'holdout_rate': hold_rate,
            'score': round(score, 2),
            'stability': round(stability, 2),
            'confidence': 'HIGH' if status == "QUALIFIED" and score >= 65 else 'MEDIUM',
            'status': status,
            'first': times[0] if times else None,
            'last': times[-1] if times else None,
            'best_time': 'N/A',
            'best_time_rate': 0,
            'version': 1,
            'parent_key': '',
            'mutation': 'DISCOVERY',
            'paper_status': 'PENDING',
            'real_time_ready': status == "QUALIFIED"
        }
    
    def discover_patterns(self, data: List[Dict]) -> List[Dict]:
        patterns = []
        nums = [x['n'] for x in data]
        times = [x['dt'] for x in data]
        
        for k in range(2, 9):
            groups = defaultdict(list)
            for i in range(len(nums) - k):
                seq = tuple(nums[i:i+k])
                if i+k < len(nums):
                    groups[seq].append((nums[i+k], times[i+k]))
            
            for seq, targets in groups.items():
                if len(targets) >= MIN_SAMPLES:
                    p = self._evaluate_pattern(f"SEQ{k}:{seq}", "SEQUENCE", seq, targets)
                    if p:
                        patterns.append(p)
        
        for hour in range(24):
            hour_data = [x for x in data if x['dt'].hour == hour]
            if len(hour_data) >= 15:
                hour_nums = [x['n'] for x in hour_data]
                for k in range(2, 5):
                    groups = defaultdict(list)
                    for i in range(len(hour_nums) - k):
                        seq = tuple(hour_nums[i:i+k])
                        if i+k < len(hour_nums):
                            groups[seq].append((hour_nums[i+k], hour_data[i+k]['dt']))
                    
                    for seq, targets in groups.items():
                        if len(targets) >= 8:
                            p = self._evaluate_pattern(f"TIME{hour}:{seq}", "TIME_SPECIFIC", seq, targets)
                            if p:
                                patterns.append(p)
        
        return patterns
    
    def learn(self) -> Dict:
        data = self.rows()
        
        if len(data) < MIN_SAMPLES:
            return {
                "records": len(data),
                "patterns": [],
                "report": f"🧠 XHAWON {XHAWON_VERSION}\n\n📦 Records: {len(data)}\n⏳ আরও data প্রয়োজন।"
            }
        
        patterns = self.discover_patterns(data)
        
        unique = {}
        for p in patterns:
            if p['key'] not in unique:
                unique[p['key']] = p
        
        patterns = list(unique.values())
        self.qualified_patterns = [p for p in patterns if p.get('status') == 'QUALIFIED']
        
        self.db.replace_patterns(patterns)
        self.db.save_experience(patterns)
        
        return {
            "records": len(data),
            "patterns": patterns,
            "regime": self._detect_regime(data),
            "report": self.generate_report(data, patterns)
        }
    
    def _detect_regime(self, data: List[Dict]) -> str:
        if len(data) < 10:
            return 'unknown'
        
        nums = [x['n'] for x in data[-20:]]
        bs = [1 if x >= 5 else 0 for x in nums]
        
        switches = sum(1 for i in range(1, len(bs)) if bs[i] != bs[i-1])
        switch_rate = switches / len(bs) if bs else 0
        
        if switch_rate > 0.6:
            return 'alternating'
        elif switch_rate < 0.3:
            return 'trending'
        else:
            return 'mixed'
    
    def generate_report(self, data: List[Dict], patterns: List[Dict]) -> str:
        q = [p for p in patterns if p.get('status') == 'QUALIFIED']
        
        L = [
            f"🧠 XHAWON {XHAWON_VERSION}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📅 {datetime.now():%d-%m-%Y %I:%M:%S %p}",
            f"📦 Records: {len(data)}",
            f"🧩 Patterns: {len(patterns)}",
            f"🏆 Qualified: {len(q)}",
            "",
            "🚀 FEATURES",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "• 👤 User Profiling & Personalization",
            "• 🤖 Google Gemini AI Integration",
            "• 📊 Advanced Pattern Discovery",
            "",
            f"🤖 Gemini AI: {'✅ ACTIVE' if self.gemini.is_available else '❌ INACTIVE'}",
            "",
            "🏆 QUALIFIED PATTERNS",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        
        if not q:
            L.append("⚪ এখনো qualified pattern নেই।")
        else:
            for i, p in enumerate(q[:10], 1):
                L += [
                    f"{i}. {p['pattern']}",
                    f"   📊 Rate: {p['rate']:.1f}% | Score: {p.get('score', 0):.1f}",
                    f"   🧬 Type: {p.get('type', 'UNKNOWN')} | Conf: {p['confidence']}",
                    ""
                ]
        
        L += [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "⚠️ এটি historical/statistical learning; কোনো ভবিষ্যৎ ফল নিশ্চিত করে না।",
            "",
            "💡 USE /my_profile for personalized insights",
            "💡 USE /gemini for AI-powered analysis"
        ]
        
        return "\n".join(L)


# ============================================================
# 4. TELEGRAM BOT
# ============================================================

class Crypto:
    def __init__(self):
        self.key = self.load_key()
        self.f = Fernet(self.key)
    
    def load_key(self):
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as f:
                key = f.read().strip()
            Fernet(key)
            return key
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        try:
            os.chmod(KEY_FILE, 0o600)
        except OSError:
            pass
        return key
    
    def enc(self, x):
        return self.f.encrypt(json.dumps(x, ensure_ascii=False).encode())
    
    def dec(self, x):
        return json.loads(self.f.decrypt(x).decode())


class DB:
    def __init__(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        self.lock = RLock()
        self.crypto = Crypto()
        self.c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.execute("PRAGMA busy_timeout=30000")
        self.init()
    
    def init(self):
        with self.lock:
            self.c.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                chat_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS results(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
                issue TEXT NOT NULL, number INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                encrypted_data TEXT NOT NULL, hash TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES users(chat_id) ON DELETE CASCADE);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_issue ON results(chat_id,issue);
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER,
                start_time TIMESTAMP, end_time TIMESTAMP, is_active INTEGER DEFAULT 0,
                total_fetched INTEGER DEFAULT 0, duration_minutes INTEGER DEFAULT 0,
                stopped_at TIMESTAMP);
            CREATE TABLE IF NOT EXISTS collector_stats(
                id INTEGER PRIMARY KEY CHECK(id=1), total_api_requests INTEGER DEFAULT 0,
                successful_requests INTEGER DEFAULT 0, failed_requests INTEGER DEFAULT 0,
                last_success TIMESTAMP, last_issue TEXT);
            INSERT OR IGNORE INTO collector_stats(id) VALUES(1);
            CREATE TABLE IF NOT EXISTS patterns(
                pattern_key TEXT PRIMARY KEY, pattern_type TEXT, pattern TEXT,
                occurrences INTEGER, correct INTEGER, incorrect INTEGER,
                success_rate REAL, recent_occurrences INTEGER, recent_correct INTEGER,
                confidence TEXT, status TEXT, first_seen TIMESTAMP, last_seen TIMESTAMP,
                updated_at TIMESTAMP);
            CREATE TABLE IF NOT EXISTS learning_state(
                id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER DEFAULT 0,
                started_at TIMESTAMP, last_cycle TIMESTAMP, next_report_at TIMESTAMP,
                total_cycles INTEGER DEFAULT 0);
            INSERT OR IGNORE INTO learning_state(id) VALUES(1);
            CREATE TABLE IF NOT EXISTS learning_reports(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                period_start TIMESTAMP, period_end TIMESTAMP, records_analyzed INTEGER,
                patterns_found INTEGER, report_text TEXT);
            CREATE TABLE IF NOT EXISTS pattern_experience(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pattern_key TEXT, pattern_type TEXT, status TEXT, score REAL,
                rate REAL, validation_rate REAL, recent_rate REAL,
                regime TEXT, best_time TEXT, action TEXT, reason TEXT);
            CREATE TABLE IF NOT EXISTS learning_audit(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event TEXT, pattern_key TEXT, details TEXT);
            CREATE TABLE IF NOT EXISTS paper_tests(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pattern_key TEXT, status TEXT, samples INTEGER, correct INTEGER, rate REAL,
                first_seen TIMESTAMP, last_seen TIMESTAMP);
            CREATE TABLE IF NOT EXISTS pattern_lineage(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pattern_key TEXT, parent_key TEXT, version INTEGER DEFAULT 1,
                mutation TEXT, reason TEXT, score REAL);
            CREATE TABLE IF NOT EXISTS paper_live(
                pattern_key TEXT PRIMARY KEY, status TEXT, samples INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0, rate REAL DEFAULT 0, started_at TIMESTAMP,
                updated_at TIMESTAMP, fail_streak INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS data_quality(
                id INTEGER PRIMARY KEY AUTOINCREMENT, checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                records INTEGER, valid INTEGER, duplicates INTEGER, invalid INTEGER,
                ordering_errors INTEGER, status TEXT, details TEXT);
            CREATE TABLE IF NOT EXISTS confidence_calibration(
                id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pattern_key TEXT, predicted_confidence REAL, observed_rate REAL,
                samples INTEGER, bin INTEGER);
            CREATE TABLE IF NOT EXISTS real_time_patterns(
                pattern_key TEXT PRIMARY KEY, pattern_text TEXT,
                last_checked TIMESTAMP, total_checks INTEGER DEFAULT 0,
                successful_checks INTEGER DEFAULT 0, current_rate REAL DEFAULT 0,
                best_hour INTEGER, best_rate REAL DEFAULT 0,
                worst_hour INTEGER, worst_rate REAL DEFAULT 0,
                recommendation_status TEXT DEFAULT 'PENDING',
                recommended_for_hours TEXT);
            CREATE TABLE IF NOT EXISTS real_time_hourly_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT, pattern_key TEXT,
                hour INTEGER, checks INTEGER DEFAULT 0,
                successful INTEGER DEFAULT 0, rate REAL DEFAULT 0,
                last_updated TIMESTAMP,
                FOREIGN KEY(pattern_key) REFERENCES real_time_patterns(pattern_key));
            """)
            self.c.commit()
    
    def user(self, cid, username, name):
        with self.lock:
            self.c.execute("""INSERT INTO users(chat_id,username,first_name) VALUES(?,?,?)
            ON CONFLICT(chat_id) DO UPDATE SET username=excluded.username,
            first_name=excluded.first_name""", (cid, username, name))
            self.c.commit()
    
    def save(self, cid, issue, number):
        try:
            issue, number = str(issue), int(number)
            if not 0 <= number <= 9:
                return False
            obj = {"chat_id": cid, "issue": issue, "number": number, "timestamp": datetime.now().isoformat()}
            raw = base64.b64encode(self.crypto.enc(obj)).decode()
            h = hashlib.sha256(f"{cid}:{issue}:{number}".encode()).hexdigest()
            with self.lock:
                cur = self.c.execute("""INSERT OR IGNORE INTO results
                (chat_id,issue,number,encrypted_data,hash) VALUES(?,?,?,?,?)""",
                                     (cid, issue, number, raw, h))
                self.c.commit()
                return cur.rowcount == 1
        except Exception as e:
            print("save:", e)
            return False
    
    def decode_rows(self, rows):
        out = []
        for r in rows:
            try:
                out.append(self.crypto.dec(base64.b64decode(r["encrypted_data"])))
            except Exception:
                pass
        return out
    
    def results(self, cid):
        with self.lock:
            rows = self.c.execute("SELECT encrypted_data FROM results WHERE chat_id=? ORDER BY id", (cid,)).fetchall()
        return self.decode_rows(rows)
    
    def all_results(self):
        with self.lock:
            rows = self.c.execute("SELECT encrypted_data FROM results ORDER BY id").fetchall()
        return self.decode_rows(rows)
    
    def count(self, cid):
        with self.lock:
            return self.c.execute("SELECT COUNT(*) FROM results WHERE chat_id=?", (cid,)).fetchone()[0]
    
    def global_count(self):
        with self.lock:
            return self.c.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    
    def session_start(self, cid, minutes):
        s = datetime.now()
        e = s + timedelta(minutes=minutes)
        with self.lock:
            self.c.execute("UPDATE sessions SET is_active=0,stopped_at=? WHERE chat_id=? AND is_active=1", (s, cid))
            self.c.execute("""INSERT INTO sessions(chat_id,start_time,end_time,is_active,duration_minutes)
            VALUES(?,?,?,?,?)""", (cid, s, e, 1, minutes))
            self.c.commit()
        return s, e
    
    def active_session(self, cid):
        with self.lock:
            return self.c.execute("""SELECT * FROM sessions WHERE chat_id=? AND is_active=1
            ORDER BY id DESC LIMIT 1""", (cid,)).fetchone()
    
    def session_add(self, cid, n):
        with self.lock:
            self.c.execute("UPDATE sessions SET total_fetched=total_fetched+? WHERE chat_id=? AND is_active=1", (n, cid))
            self.c.commit()
    
    def session_end(self, cid):
        with self.lock:
            self.c.execute("UPDATE sessions SET is_active=0,stopped_at=? WHERE chat_id=? AND is_active=1",
                           (datetime.now(), cid))
            self.c.commit()
    
    def api_stat(self, ok, issue=None):
        with self.lock:
            if ok:
                self.c.execute("""UPDATE collector_stats SET total_api_requests=total_api_requests+1,
                successful_requests=successful_requests+1,last_success=?,last_issue=? WHERE id=1""",
                               (datetime.now(), issue))
            else:
                self.c.execute("""UPDATE collector_stats SET total_api_requests=total_api_requests+1,
                failed_requests=failed_requests+1 WHERE id=1""")
            self.c.commit()
    
    def api(self):
        with self.lock:
            return self.c.execute("SELECT * FROM collector_stats WHERE id=1").fetchone()
    
    def learning(self, enabled=None):
        with self.lock:
            if enabled is True:
                n = datetime.now()
                self.c.execute("UPDATE learning_state SET enabled=1,started_at=?,next_report_at=? WHERE id=1",
                               (n, n + timedelta(hours=REPORT_HOURS)))
                self.c.commit()
            elif enabled is False:
                self.c.execute("UPDATE learning_state SET enabled=0 WHERE id=1")
                self.c.commit()
            return self.c.execute("SELECT * FROM learning_state WHERE id=1").fetchone()
    
    def cycle(self):
        with self.lock:
            self.c.execute("UPDATE learning_state SET last_cycle=?,total_cycles=total_cycles+1 WHERE id=1",
                           (datetime.now(),))
            self.c.commit()
    
    def replace_patterns(self, ps):
        with self.lock:
            self.c.execute("DELETE FROM patterns")
            for p in ps:
                self.c.execute("""INSERT INTO patterns VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                               (p.get("key"), p.get("type"), p.get("pattern"), p.get("n", 0),
                                p.get("correct", 0), p.get("wrong", 0), p.get("rate", 0),
                                p.get("recent_n", 0), p.get("recent_correct", 0),
                                p.get("confidence", "LOW"), p.get("status", "REVIEW"),
                                p.get("first"), p.get("last"), datetime.now()))
            self.c.commit()
    
    def report_save(self, a, b, n, p, text):
        with self.lock:
            self.c.execute("""INSERT INTO learning_reports(period_start,period_end,records_analyzed,
            patterns_found,report_text) VALUES(?,?,?,?,?)""", (a, b, n, p, text))
            self.c.commit()
    
    def save_experience(self, records):
        if not records:
            return
        with self.lock:
            for r in records:
                self.c.execute(
                    """INSERT INTO pattern_experience
                    (pattern_key,pattern_type,status,score,rate,validation_rate,recent_rate,
                     regime,best_time,action,reason)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.get("key"), r.get("type"), r.get("status"), r.get("score", 0),
                     r.get("rate", 0), r.get("validation_rate", 0), r.get("recent_rate", 0),
                     r.get("regime", "UNKNOWN"), r.get("best_time", "N/A"),
                     r.get("action", "REVIEW"), r.get("reason", "")))
            self.c.commit()
    
    def audit(self, event, pattern_key="", details=""):
        with self.lock:
            self.c.execute("INSERT INTO learning_audit(event,pattern_key,details) VALUES(?,?,?)",
                           (event, pattern_key, json.dumps(details, ensure_ascii=False) if isinstance(details,
                                                                                                     (dict, list)) else str(
                               details)))
            self.c.commit()
    
    def save_paper_test(self, p):
        with self.lock:
            self.c.execute("INSERT INTO paper_tests(pattern_key,status,samples,correct,rate,first_seen,last_seen) VALUES(?,?,?,?,?,?,?)",
                           (p.get("key"), p.get("paper_status", "PENDING"), p.get("paper_n", 0), p.get("paper_correct", 0),
                            p.get("paper_rate", 0), p.get("first"), p.get("last")))
            self.c.commit()
    
    def save_lineage(self, records):
        if not records:
            return
        with self.lock:
            for r in records:
                self.c.execute("""INSERT INTO pattern_lineage
                (pattern_key,parent_key,version,mutation,reason,score) VALUES(?,?,?,?,?,?)""",
                               (r.get("key"), r.get("parent_key", ""), r.get("version", 1), r.get("mutation", "DISCOVERY"),
                                r.get("reason", ""), r.get("score", 0)))
            self.c.commit()
    
    def update_paper_live(self, records):
        if not records:
            return
        with self.lock:
            for r in records:
                self.c.execute("""INSERT INTO paper_live(pattern_key,status,samples,correct,rate,started_at,updated_at,fail_streak)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(pattern_key) DO UPDATE SET
                status=excluded.status,samples=excluded.samples,correct=excluded.correct,rate=excluded.rate,
                updated_at=excluded.updated_at,fail_streak=excluded.fail_streak""",
                               (r.get("key"), r.get("paper_live_status", "PENDING"), r.get("paper_live_n", 0),
                                r.get("paper_live_correct", 0), r.get("paper_live_rate", 0), r.get("paper_started"),
                                datetime.now(), r.get("paper_fail_streak", 0)))
            self.c.commit()
    
    def save_quality(self, records):
        if not records:
            return
        with self.lock:
            for r in records:
                self.c.execute("""INSERT INTO data_quality(records,valid,duplicates,invalid,ordering_errors,status,details)
                VALUES(?,?,?,?,?,?,?)""",
                               (r.get("records", 0), r.get("valid", 0), r.get("duplicates", 0),
                                r.get("invalid", 0), r.get("ordering_errors", 0), r.get("status", "UNKNOWN"),
                                json.dumps(r.get("details", {}), ensure_ascii=False)))
            self.c.commit()
    
    def save_calibration(self, records):
        if not records:
            return
        with self.lock:
            for r in records:
                self.c.execute("""INSERT INTO confidence_calibration
                (pattern_key,predicted_confidence,observed_rate,samples,bin) VALUES(?,?,?,?,?)""",
                               (r.get("key"), r.get("predicted", 0), r.get("observed", 0), r.get("samples", 0),
                                r.get("bin", 0)))
            self.c.commit()
    
    def reset(self, cid):
        with self.lock:
            self.c.execute("DELETE FROM results WHERE chat_id=?", (cid,))
            self.c.execute("DELETE FROM sessions WHERE chat_id=?", (cid,))
            self.c.commit()
    
    def backup(self):
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(BACKUP_DIR, f"backup_{stamp}.zip")
            with self.lock:
                self.c.execute("PRAGMA wal_checkpoint(FULL)")
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                for f in (DB_PATH, KEY_FILE):
                    if os.path.exists(f):
                        z.write(f, os.path.basename(f))
            return path
        except Exception as e:
            print("backup:", e)
            return None
    
    def save_real_time_pattern(self, pattern_key, pattern_text):
        with self.lock:
            self.c.execute("""INSERT OR IGNORE INTO real_time_patterns
            (pattern_key, pattern_text, last_checked) VALUES(?,?,?)""",
                          (pattern_key, pattern_text, datetime.now()))
            self.c.commit()
    
    def update_real_time_stats(self, pattern_key, hour, success):
        with self.lock:
            self.c.execute("""INSERT INTO real_time_hourly_stats
            (pattern_key, hour, checks, successful, rate, last_updated)
            VALUES(?,?,1,?,?,?)
            ON CONFLICT DO UPDATE SET
            checks=checks+1, successful=successful+?,
            rate=CAST(successful AS REAL)/checks*100,
            last_updated=?""",
            (pattern_key, hour, 1 if success else 0,
             (successful := 1 if success else 0),
             datetime.now()))
            self.c.commit()
            
            self.c.execute("""UPDATE real_time_patterns SET
            total_checks=total_checks+1,
            successful_checks=successful_checks+?,
            current_rate=CAST(successful_checks AS REAL)/total_checks*100,
            last_checked=?
            WHERE pattern_key=?""",
            (1 if success else 0, datetime.now(), pattern_key))
            self.c.commit()
    
    def get_real_time_recommendations(self, min_checks=20, min_rate=55.0):
        with self.lock:
            rows = self.c.execute("""
                SELECT pattern_key, pattern_text, total_checks, successful_checks,
                       current_rate, best_hour, best_rate,
                       recommended_for_hours
                FROM real_time_patterns
                WHERE total_checks >= ? AND current_rate >= ?
                ORDER BY current_rate DESC, total_checks DESC
                LIMIT 10
            """, (min_checks, min_rate)).fetchall()
            return [dict(row) for row in rows]
    
    def update_recommendation(self, pattern_key, best_hour, best_rate, recommended_hours):
        with self.lock:
            self.c.execute("""UPDATE real_time_patterns SET
            best_hour=?, best_rate=?, recommended_for_hours=?,
            recommendation_status='ACTIVE'
            WHERE pattern_key=?""",
            (best_hour, best_rate, recommended_hours, pattern_key))
            self.c.commit()
    
    def get_hourly_performance(self, pattern_key):
        with self.lock:
            rows = self.c.execute("""
                SELECT hour, checks, successful, rate
                FROM real_time_hourly_stats
                WHERE pattern_key=?
                ORDER BY hour
            """, (pattern_key,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_all_active_recommendations(self):
        with self.lock:
            rows = self.c.execute("""
                SELECT pattern_key, pattern_text, current_rate,
                       best_hour, best_rate, recommended_for_hours,
                       recommendation_status
                FROM real_time_patterns
                WHERE recommendation_status='ACTIVE'
                ORDER BY current_rate DESC
            """).fetchall()
            return [dict(row) for row in rows]
    
    def close(self):
        self.c.close()


# ============================================================
# 5. TELEGRAM BOT MAIN CLASS
# ============================================================

class Bot:
    def __init__(self):
        self.db = DB()
        self.learner = UltimateLearner(self.db)
        self.app = None
        self.tasks = {}
        self.events = {}
        self.lt = None
        self.lstop = asyncio.Event()
        self.reports = {}
    
    def kb(self):
        on = bool(self.db.learning()["enabled"])
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 ৩০ মিনিট", callback_data="duration_30"),
             InlineKeyboardButton("🔄 ৬০ মিনিট", callback_data="duration_60")],
            [InlineKeyboardButton("🔄 ১২০ মিনিট", callback_data="duration_120"),
             InlineKeyboardButton("🔄 ২৪ ঘণ্টা", callback_data="duration_1440")],
            [InlineKeyboardButton(f"🧠 Learning: {'🟢 ON' if on else '🔴 OFF'}", callback_data="learning")],
            [InlineKeyboardButton("👤 My Profile", callback_data="my_profile")],
            [InlineKeyboardButton("🤖 Gemini Insights", callback_data="gemini_insights")],
            [InlineKeyboardButton("🧠 Ultimate Report", callback_data="lreport")],
            [InlineKeyboardButton("📡 Live Recommendations", callback_data="live_recs")],
            [InlineKeyboardButton("📊 Number Report", callback_data="nreport"),
             InlineKeyboardButton("📊 BIG/SMALL", callback_data="bsreport")],
            [InlineKeyboardButton("📥 PDF", callback_data="pdf")],
            [InlineKeyboardButton("💾 Admin Backup", callback_data="backup")],
            [InlineKeyboardButton("🛑 Stop", callback_data="stop"), InlineKeyboardButton("🗑️ Reset", callback_data="reset")]
        ])
    
    async def start(self, u, c):
        cid = u.effective_chat.id
        x = u.effective_user
        self.db.user(cid, x.username, x.first_name)
        
        self.learner.profiler.update_profile(cid, {
            'username': x.username or "Unknown"
        })
        
        gemini_status = "🟢 ACTIVE" if self.learner.gemini.is_available else "🔴 INACTIVE"
        
        await u.message.reply_text(
            f"🧠 XHAWON {XHAWON_VERSION}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Your records: {self.db.count(cid)}\n🌐 Global: {self.db.global_count()}\n"
            f"🧠 Learning: {'🟢 ON' if self.db.learning()['enabled'] else '🔴 OFF'}\n"
            f"🤖 Gemini AI: {gemini_status}\n\n"
            "🚀 **FEATURES:**\n"
            "• 👤 Personalized User Profiles\n"
            "• 🤖 Google Gemini AI Integration\n"
            "• 📊 Advanced Pattern Discovery\n"
            "• 📈 Real-time Monitoring\n\n"
            "নিচের button ব্যবহার করুন।", reply_markup=self.kb())
    
    async def cb(self, u, c):
        q = u.callback_query
        await q.answer()
        cid = q.message.chat_id
        d = q.data
        
        if d.startswith("duration_"):
            await self.start_collect(cid, int(d.split("_")[1]), q)
        elif d == "learning":
            await self.toggle(cid, q)
        elif d == "my_profile":
            await self.my_profile(cid, q)
        elif d == "gemini_insights":
            await self.gemini_insights(cid, q)
        elif d == "lreport":
            await self.lreport(cid, q)
        elif d == "live_recs":
            await self.live_recommendations(cid, q)
        elif d == "nreport":
            await self.nreport(cid, q)
        elif d == "bsreport":
            await self.bsreport(cid, q)
        elif d == "pdf":
            await self.pdf(cid, q)
        elif d == "backup":
            await self.backup(cid, q)
        elif d == "stop":
            await self.stop(cid, q)
        elif d == "reset":
            await self.reset(cid, q)
        elif d == "main":
            await q.edit_message_text("🏠 XHAWON MAIN MENU", reply_markup=self.kb())
    
    async def my_profile(self, cid, q):
        insights = self.learner.profiler.generate_user_insights(cid)
        await q.edit_message_text(
            insights,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="my_profile")],
                [InlineKeyboardButton("🏠 Main", callback_data="main")]
            ]),
            parse_mode='Markdown'
        )
    
    async def gemini_insights(self, cid, q):
        if not self.learner.gemini.is_available:
            await q.edit_message_text(
                "❌ Gemini AI is not available.\n"
                "Please set GEMINI_API_KEY in environment variables.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main")]])
            )
            return
        
        await q.edit_message_text("🤖 Getting Gemini insights... Please wait...")
        
        data = self.learner.rows()
        patterns = self.learner.qualified_patterns
        
        if not patterns:
            await q.edit_message_text(
                "⚠️ No qualified patterns found. Collect more data first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main")]])
            )
            return
        
        analysis = await self.learner.gemini.analyze_patterns(patterns, data)
        
        if analysis.get('error'):
            await q.edit_message_text(
                f"❌ Error: {analysis['error']}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main")]])
            )
            return
        
        result = "🤖 **GEMINI AI MARKET ANALYSIS**\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if analysis.get('analysis'):
            paragraphs = analysis['analysis'].split('\n\n')
            for p in paragraphs[:5]:
                result += p + "\n\n"
        
        await q.edit_message_text(
            result,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="gemini_insights")],
                [InlineKeyboardButton("🏠 Main", callback_data="main")]
            ]),
            parse_mode='Markdown'
        )
    
    async def live_recommendations(self, cid, q):
        recs = self.db.get_all_active_recommendations()
        
        if not recs:
            await q.edit_message_text(
                "📡 No live recommendations yet. Keep collecting data.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main")]])
            )
            return
        
        L = ["📡 **LIVE RECOMMENDATIONS**", "━━━━━━━━━━━━━━━━━━━━", ""]
        
        for i, rec in enumerate(recs[:10], 1):
            pattern = rec.get("pattern_text", "Unknown")
            rate = rec.get("current_rate", 0)
            checks = rec.get("total_checks", 0)
            best_hour = rec.get("best_hour", 0)
            
            L.append(f"{i}. 🔍 {pattern}")
            L.append(f"   📊 Rate: {rate:.1f}% ({checks} checks)")
            L.append(f"   ⏰ Best: {best_hour:02d}:00")
            L.append("")
        
        await q.edit_message_text(
            "\n".join(L),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="live_recs")],
                [InlineKeyboardButton("🏠 Main", callback_data="main")]
            ]),
            parse_mode='Markdown'
        )
    
    async def start_collect(self, cid, minutes, q):
        if self.tasks.get(cid) and not self.tasks[cid].done():
            await q.edit_message_text("⚠️ Collection ইতিমধ্যে চলছে।", reply_markup=self.kb())
            return
        
        s, e = self.db.session_start(cid, minutes)
        ev = asyncio.Event()
        self.events[cid] = ev
        self.tasks[cid] = asyncio.create_task(self.collect(cid, s, e, ev))
        
        dur = f"{minutes // 60} ঘণ্টা {minutes % 60} মিনিট" if minutes >= 60 else f"{minutes} মিনিট"
        await q.edit_message_text(f"🚀 DATA COLLECTION STARTED\n━━━━━━━━━━━━━━━━━━━━\n\n⏰ {dur}\n🕐 {s:%I:%M:%S %p}\n🏁 {e:%I:%M:%S %p}\n\n📡 API monitoring চলছে...",
                                  reply_markup=self.kb())
    
    async def fetch(self):
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout,
                                         headers={"User-Agent": "Mozilla/5.0 XhawonCollector"}) as s:
            async with s.get(API_URL, params={"pageNo": 1, "pageSize": 100}) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                return await r.json(content_type=None)
    
    @staticmethod
    def parse(d):
        try:
            items = d["data"]["list"]
        except (TypeError, KeyError):
            return []
        
        out = []
        for x in items:
            try:
                issue = x["issueNumber"]
                n = int(x["number"])
                if 0 <= n <= 9:
                    out.append({"issue": str(issue), "number": n})
            except (KeyError, TypeError, ValueError):
                pass
        return out
    
    async def collect(self, cid, s, e, ev):
        new = 0
        try:
            while datetime.now() < e and not ev.is_set():
                try:
                    items = self.parse(await self.fetch())
                    if not items:
                        self.db.api_stat(False)
                        await asyncio.sleep(POLL_INTERVAL)
                        continue
                    
                    self.db.api_stat(True, items[0]["issue"])
                    n = 0
                    for x in items:
                        if self.db.save(cid, x["issue"], x["number"]):
                            n += 1
                    
                    if n:
                        new += n
                        self.db.session_add(cid, n)
                    
                    await asyncio.sleep(POLL_INTERVAL)
                except asyncio.CancelledError:
                    raise
                except Exception as ex:
                    print("collector:", ex)
                    self.db.api_stat(False)
                    await asyncio.sleep(3)
        finally:
            self.db.session_end(cid)
            self.events.pop(cid, None)
            self.tasks.pop(cid, None)
            try:
                await self.app.bot.send_message(cid,
                    ("🛑 COLLECTION STOPPED" if ev.is_set() else "✅ COLLECTION COMPLETED") + f"\n━━━━━━━━━━━━━━━━━━━━\n🆕 New: {new}\n📦 Total: {self.db.count(cid)}",
                    reply_markup=self.kb())
            except Exception as ex:
                print("completion:", ex)
    
    async def stop(self, cid, q=None):
        ev = self.events.get(cid)
        task = self.tasks.get(cid)
        
        if ev:
            ev.set()
        if task and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), 5)
            except asyncio.TimeoutError:
                task.cancel()
            except Exception:
                pass
        
        self.db.session_end(cid)
        if q:
            await q.edit_message_text("🛑 Collection বন্ধ করা হয়েছে।", reply_markup=self.kb())
    
    async def stop_cmd(self, u, c):
        await self.stop(u.effective_chat.id)
        await u.message.reply_text("🛑 Collection বন্ধ।", reply_markup=self.kb())
    
    async def toggle(self, cid, q):
        if self.db.learning()["enabled"]:
            self.db.learning(False)
            self.lstop.set()
            if self.lt and not self.lt.done():
                self.lt.cancel()
            self.lt = None
            await q.edit_message_text("🧠 LEARNING AI: 🔴 OFF", reply_markup=self.kb())
            return
        
        self.db.learning(True)
        self.lstop = asyncio.Event()
        if not self.lt or self.lt.done():
            self.lt = asyncio.create_task(self.learning_loop())
        
        try:
            r = await asyncio.to_thread(self.learner.learn)
            self.reports[cid] = r["report"]
        except Exception as e:
            print("initial learning:", e)
        
        await q.edit_message_text(
            "🧠 LEARNING AI: 🟢 ON\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Pattern discovery active\n"
            "📈 Performance tracking active\n"
            "📡 Real-time monitoring active\n"
            "📋 ২৪ ঘণ্টার report cycle active\n\n"
            "ALL SYSTEMS: ON", reply_markup=self.kb())
    
    async def learning_loop(self):
        last = datetime.now()
        while not self.lstop.is_set():
            try:
                if not self.db.learning()["enabled"]:
                    break
                
                r = await asyncio.to_thread(self.learner.learn)
                now = datetime.now()
                
                if now - last >= timedelta(hours=REPORT_HOURS):
                    self.db.report_save(last, now, r["records"], len(r.get("patterns", [])), r["report"])
                    if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_CHAT_ID_HERE" and ADMIN_CHAT_ID.strip().isdigit():
                        try:
                            await self.app.bot.send_message(int(ADMIN_CHAT_ID.strip()), r["report"])
                        except Exception as e:
                            print("admin report:", e)
                    last = now
                
                self.db.cycle()
                try:
                    await asyncio.wait_for(self.lstop.wait(), LEARNING_POLL)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                print("learning:", e)
                await asyncio.sleep(10)
    
    async def lreport(self, cid, q):
        r = await asyncio.to_thread(self.learner.learn)
        self.reports[cid] = r["report"]
        await q.edit_message_text(r["report"], reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 PDF", callback_data="pdf")],
            [InlineKeyboardButton("🤖 Gemini Insights", callback_data="gemini_insights")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="lreport"), InlineKeyboardButton("🏠 Main", callback_data="main")]
        ]))
    
    async def nreport(self, cid, q):
        rows = self.db.results(cid)
        if len(rows) < 10:
            await q.edit_message_text("⚠️ কমপক্ষে ১০টি record প্রয়োজন।", reply_markup=self.kb())
            return
        
        nums = [int(x["number"]) for x in rows]
        L = ["📊 NUMBER TRANSITION REPORT", "━━━━━━━━━━━━━━━━━━━━", f"📦 Records: {len(nums)}", ""]
        
        for n in range(10):
            vals = [nums[i + 1] for i in range(len(nums) - 1) if nums[i] == n]
            L.append(f"🔢 {n} →")
            if not vals:
                L.append("   ⚠️ No data")
                continue
            
            c = Counter(vals)
            total = len(vals)
            for x in range(10):
                L.append(f"   {x}: {c.get(x, 0)} ({c.get(x, 0) / total * 100:.1f}%)")
            
            a, b = c.most_common(1)[0]
            L.append(f"   🏆 Most common: {a} ({b / total * 100:.1f}%)")
            L.append("")
        
        L.append("⚠️ Historical statistics only.")
        self.reports[cid] = "\n".join(L)
        await q.edit_message_text(self.reports[cid], reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📥 PDF", callback_data="pdf")],
             [InlineKeyboardButton("🤖 Gemini Insights", callback_data="gemini_insights")],
             [InlineKeyboardButton("🏠 Main", callback_data="main")]]))
    
    async def bsreport(self, cid, q):
        rows = self.db.results(cid)
        if len(rows) < 10:
            await q.edit_message_text("⚠️ কমপক্ষে ১০টি record প্রয়োজন।", reply_markup=self.kb())
            return
        
        nums = [int(x["number"]) for x in rows]
        m = {"BIG": {"BIG": 0, "SMALL": 0}, "SMALL": {"BIG": 0, "SMALL": 0}}
        t = {"BIG": 0, "SMALL": 0}
        
        for a, b in zip(nums, nums[1:]):
            x = "BIG" if a >= 5 else "SMALL"
            y = "BIG" if b >= 5 else "SMALL"
            m[x][y] += 1
            t[x] += 1
        
        L = ["📊 BIG/SMALL TRANSITION REPORT", "━━━━━━━━━━━━━━━━━━━━"]
        for x in ("BIG", "SMALL"):
            L.append(f"📌 {x}")
            for y in ("BIG", "SMALL"):
                v = m[x][y]
                L.append(f"   → {y}: {v} ({v / t[x] * 100:.2f}%)" if t[x] else f"   → {y}: 0 (0%)")
        
        L.append("\n⚠️ Historical statistics only.")
        self.reports[cid] = "\n".join(L)
        await q.edit_message_text(self.reports[cid], reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📥 PDF", callback_data="pdf")],
             [InlineKeyboardButton("🤖 Gemini Insights", callback_data="gemini_insights")],
             [InlineKeyboardButton("🏠 Main", callback_data="main")]]))
    
    async def pdf(self, cid, q):
        text = self.reports.get(cid)
        if not text:
            await q.edit_message_text("⚠️ আগে report generate করুন।", reply_markup=self.kb())
            return
        
        buf = io.BytesIO()
        p = canvas.Canvas(buf, pagesize=A4)
        _, h = A4
        y = h - 40
        p.setFont("Helvetica", 9)
        
        for line in text.splitlines():
            if y < 40:
                p.showPage()
                p.setFont("Helvetica", 9)
                y = h - 40
            p.drawString(40, y, line.encode("ascii", "replace").decode()[:110])
            y -= 14
        
        p.save()
        buf.seek(0)
        await q.message.reply_document(document=buf, filename=f"XHAWON_{datetime.now():%Y%m%d_%H%M}.pdf")
    
    async def backup(self, cid, q):
        if not ADMIN_CHAT_ID or ADMIN_CHAT_ID == "YOUR_CHAT_ID_HERE" or str(cid) != ADMIN_CHAT_ID:
            await q.edit_message_text("⛔ শুধু configured admin backup নিতে পারবেন।", reply_markup=self.kb())
            return
        
        await q.edit_message_text("⏳ Backup তৈরি হচ্ছে...")
        path = await asyncio.to_thread(self.db.backup)
        if path:
            await q.message.reply_document(document=path, caption="💾 XHAWON BACKUP")
        else:
            await q.message.reply_text("❌ Backup failed.")
    
    async def reset(self, cid, q):
        await self.stop(cid)
        self.db.reset(cid)
        self.reports.pop(cid, None)
        await q.edit_message_text("🗑️ আপনার collection data reset করা হয়েছে।", reply_markup=self.kb())
    
    async def status(self, u, c):
        cid = u.effective_chat.id
        st = self.db.learning()
        a = self.db.api()
        recs = self.db.get_all_active_recommendations()
        
        await u.message.reply_text(f"📊 XHAWON STATUS\n━━━━━━━━━━━━━━━━━━━━\n"
                                   f"📦 Your records: {self.db.count(cid)}\n🌐 Global: {self.db.global_count()}\n"
                                   f"📡 Collection: {'🟢 ON' if self.db.active_session(cid) else '🔴 OFF'}\n"
                                   f"🧠 Learning: {'🟢 ON' if st['enabled'] else '🔴 OFF'}\n"
                                   f"📡 Live Recs: {len(recs)} active\n"
                                   f"🌐 API requests: {a['total_api_requests']}\n✅ Success: {a['successful_requests']}\n"
                                   f"❌ Failed: {a['failed_requests']}\n📌 Last issue: {a['last_issue'] or 'N/A'}")
    
    async def help(self, u, c):
        await u.message.reply_text(
            f"📖 XHAWON HELP {XHAWON_VERSION}\n━━━━━━━━━━━━━━━━━━━━\n\n"
            "/start — Main menu\n"
            "/status — System status\n"
            "/stop_collect — Stop collection\n"
            "/help — This help\n\n"
            "👤 **USER PROFILE:**\n"
            "• Tracks your progress\n"
            "• Personalized recommendations\n\n"
            "🤖 **GEMINI AI:**\n"
            "• Pattern analysis\n"
            "• Market insights\n\n"
            "📊 **PATTERNS:**\n"
            "• Automatic discovery\n"
            "• Real-time monitoring\n"
            "• Performance tracking"
        )
    
    async def post_init(self, app):
        self.app = app
        if self.db.learning()["enabled"]:
            self.lstop = asyncio.Event()
            self.lt = asyncio.create_task(self.learning_loop())
    
    async def post_shutdown(self, app):
        self.lstop.set()
        if self.lt and not self.lt.done():
            self.lt.cancel()
        self.db.close()
    
    def run(self):
        self.app = (Application.builder().token(BOT_TOKEN)
                   .post_init(self.post_init)
                   .post_shutdown(self.post_shutdown)
                   .build())
        
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("stop_collect", self.stop_cmd))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CallbackQueryHandler(self.cb))
        
        print("=" * 60)
        print(f"🚀 XHAWON {XHAWON_VERSION} STARTED")
        print("=" * 60)
        print(f"🤖 BOT_TOKEN: {'✅ Set' if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ Missing'}")
        print(f"🤖 Gemini AI: {'✅ ACTIVE' if self.learner.gemini.is_available else '❌ INACTIVE'}")
        print(f"👤 User Profiling: ✅ ACTIVE")
        print("=" * 60)
        print("🔥 XHAWON is READY!")
        print("=" * 60)
        
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


# ============================================================
# 6. ENTRYPOINT
# ============================================================

def main():
    """Main entry point for XHAWON Bot"""
    try:
        bot = Bot()
        bot.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
