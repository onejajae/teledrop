"""
Slug 생성 유틸리티

사용자 친화적인 slug를 생성하기 위한 함수들을 제공합니다.
영어 단어 3개 조합 (명사-동사-형용사) 형태로 기억하기 쉬운 slug를 생성합니다.

예시: "cat-dance-happy", "tree-sing-bright", "book-fly-gentle"
"""

import random
import time

# ═══════════════════════════════════════════════════════════════
# 📝 단어 목록 정의 (알파벳 순으로 정렬)
# ═══════════════════════════════════════════════════════════════

# 명사 (88개) - 동물, 자연, 음식, 물건
NOUNS = [
    # 동물 (34개)
    "ant", "bat", "bear", "bee", "bird", "butterfly", "cat", "cow", "crab", "deer", "dog", "dolphin",
    "duck", "eagle", "elephant", "fish", "fox", "frog", "giraffe", "goat", "horse", "lion", "mouse",
    "owl", "panda", "penguin", "pig", "rabbit", "seal", "sheep", "snake", "turtle", "whale", "wolf", "zebra",
    
    # 자연 (32개)
    "beach", "cloud", "earth", "fire", "flower", "forest", "grass", "ground", "hill", "ice", "lake", "leaf", "mars", "moon", "mountain",
    "ocean", "rain", "river", "rock", "sand", "sea", "sky", "snow", "space", "star", "stone", "sun", "time", "tree", 
    "valley", "water", "wind",
    
    # 음식 (24개)
    "apple", "banana", "bread", "burger", "cake", "candy", "cheese", "cookie", "corn", "egg", "grape", "honey", 
    "juice", "meat", "milk", "nut", "pasta", "pizza", "rice", "salad", "sandwich", "soup", "tea", "yogurt",
    
    # 물건 (27개)
    "bag", "ball", "base", "bike", "book", "box", "camera", "car", "chair", "clock", "cup", "desk", "door", "guitar", "hat", "key", 
    "lamp", "mirror", "page", "pen", "phone", "plate", "shoe", "sofa", "toy", "watch", "window"
]

# 추상명사 (27개) - 감정, 개념, 에너지
ABSTRACTS = [
    "adventure", "beauty", "class", "courage", "dream", "energy", "faith", "game", "glory", "heart", "honor", 
    "idea", "joy", "life", "love", "luck", "magic", "mind", "mystery", "news", "peace", "plan", "power", "soul", "spark", "spirit", "truth"
]

# 방향/위치 (21개) - 짧은 방향 표현
DIRECTIONS = [
    "back", "bottom", "center", "down", "east", "far", "front", "in", "left", "middle", "near", "north", "out", "over", "right", "side", "south", "top", "under", "up", "west"
]

# 의성어 (24개) - 소리 표현
SOUNDS = [
    "bam", "bang", "beep", "boom", "buzz", "chirp", "clap", "click", "crash", "honk", "hum", "ping", "pop", "pow", 
    "ring", "snap", "splash", "thud", "tick", "whoosh", "wow", "zap", "zip", "zoom"
]

# 고유명사 (40개) - 도시명, 영어 이름
NAMES = [
    # 도시명 (22개)
    "Austin", "Bangkok", "Berlin", "Boston", "Cairo", "Dallas", "Dubai", "Lima", "London", "Miami", "Mumbai", 
    "Oslo", "Paris", "Phoenix", "Prague", "Rome", "Seoul", "Sydney", "Tokyo", "Vegas", "Vienna", "Zurich",
    
    # 영어 이름 (30개)  
    "Alex", "Alice", "Amy", "Anna", "Ben", "Bob", "Charlie", "David", "Emma", "Grace", "Ivy", "Jack", "Jane", 
    "Jim", "John", "Kate", "Kim", "Leo", "Lisa", "Lucy", "Luke", "Mary", "Max", "Mike", "Rose", "Sam", "Sara", "Sophie", "Tom", "Zoe"
]

# 날짜 (19개) - 월, 요일
DATES = [
    # 월 (12개)
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December",
    
    # 요일 (7개)
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

# 숫자 (28개) - 기본 숫자, 10의 배수, 큰 수, 컴퓨터 단위
NUMBERS = [
    # 기본 숫자 (12개)
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
    
    # 10의 배수 (6개)
    "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
    
    # 큰 수 (2개)
    "Hundred", "Thousand",
    
    # 컴퓨터 단위 (8개)
    "Kilo", "Mega", "Giga", "Tera", "Byte", "Bit", "Pixel", "Hertz"
]

# 포네틱 코드 (21개) - NATO 표준 알파벳 (중복 제외)
PHONETIC = [
    # NATO 포네틱 알파벳 (중복되는 Charlie, Lima, Mike, November, Kilo 제외)
    "Alpha", "Bravo", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet",
    "Oscar", "Papa", "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", 
    "Whiskey", "Xray", "Yankee", "Zulu"
]

# 동사 (70개) - 기본 동작, 감정/상태, 창작 활동, 개발 용어
VERBS = [
    # 기본 동작 (46개)
    "ask", "bounce", "build", "call", "catch", "climb", "close", "cook", "dance", "draw", "drop", "eat", "find", "fly", "get", "give", "go",
    "hit", "hold", "jump", "kick", "look", "make", "open", "play", "read", "roll", "run", "set", "sing", "sleep", "slide", "spin",
    "start", "stop", "swim", "take", "tell", "throw", "try", "turn", "wait", "walk", "win", "work", "write",
    
    # 감정/상태 (24개)
    "believe", "care", "enjoy", "explore", "fear", "feel", "focus", "hear", "help", "laugh",
    "learn", "like", "move", "relax", "remember", "rest", "see", "share", "smile", 
    "think", "trust", "visit", "wish", "worry",
    
    # 창작 활동 (5개)
    "craft", "create", "design", "invent", "paint",
    
    # 개발 용어 (20개)
    "backup", "code", "commit", "compile", "debug", "delete", "deploy", "fix", "hack", "install", "load", "merge", "post", 
    "pull", "push", "save", "send", "sync", "test", "update"
]

# 형용사 (55개) - 긍정적 특성, 색깔, 크기/특성
ADJECTIVES = [
    # 긍정적 특성 (38개)
    "bad", "brave", "bright", "calm", "cheerful", "clean", "clever", "cool", "creative", "curious", "easy", "elegant",
    "fast", "free", "fresh", "gentle", "good", "graceful", "happy", "hard", "honest", "kind", "loyal", "new", "nice", "old", "patient", 
    "peaceful", "quick", "real", "safe", "slow", "smart", "soft", "strong", "true", "wise", "young",
    
    # 색깔 (18개)
    "black", "blue", "cold", "coral", "dark", "deep", "gold", "gray", "green", "light", "orange", "pink", 
    "purple", "red", "silver", "warm", "white", "yellow",
    
    # 크기/특성 (19개)
    "big", "empty", "full", "heavy", "high", "hot", "long", "loud", "poor", "quiet", "rich", "round", "rough", "shiny",
    "small", "smooth", "thick", "tiny", "wide"
]


# ═══════════════════════════════════════════════════════════════
# 🎲 Slug 생성 함수들
# ═══════════════════════════════════════════════════════════════

def generate_slug(seed: int = None) -> str:
    """
    영어 단어 3개 조합으로 slug를 무작위 생성합니다.
    
    30가지 패턴 중 하나를 무작위로 선택하여 생성:
    - 기본: 명사-동사-형용사, 형용사-명사-동사, 추상명사-명사-동사
    - 의성어: 의성어-명사-형용사, 형용사-의성어-명사, 추상명사-의성어-형용사, 의성어-추상명사-명사, 방향-의성어-형용사, 의성어-날짜-명사
    - 방향: 방향-추상명사-동사, 방향-날짜-명사, 방향-숫자-명사
    - 고유명사: 고유명사-명사-동사, 명사-고유명사-형용사, 고유명사-동사-형용사, 형용사-고유명사-명사
    - 날짜: 날짜-명사-동사, 명사-날짜-형용사, 날짜-동사-형용사, 형용사-날짜-명사, 추상명사-날짜-명사
    - 숫자: 숫자-명사-동사, 명사-숫자-형용사, 숫자-동사-형용사, 형용사-숫자-명사, 추상명사-숫자-명사
    - 포네틱: 포네틱-명사-동사, 명사-포네틱-형용사, 포네틱-동사-형용사, 형용사-포네틱-명사
    
    Args:
        seed: 테스트용 랜덤 시드 (선택적, None이면 완전 랜덤)
    
    Returns:
        str: 생성된 slug (예: "cat-dance-happy", "alpha-cat-sing", "bravo-fly-bright")
    """
    # 테스트용 시드 설정
    if seed is not None:
        random.seed(seed)
    
    # 각 품사에서 단어 선택
    noun = random.choice(NOUNS)
    verb = random.choice(VERBS) 
    adjective = random.choice(ADJECTIVES)
    abstract = random.choice(ABSTRACTS)
    direction = random.choice(DIRECTIONS)
    sound = random.choice(SOUNDS)
    name = random.choice(NAMES)
    date = random.choice(DATES)
    number = random.choice(NUMBERS)
    phonetic = random.choice(PHONETIC)
    
    # 모든 패턴 정의 (30개)
    patterns = [
        # 기본 패턴 (3개)
        f"{noun}-{verb}-{adjective}",          # 명사-동사-형용사
        f"{adjective}-{noun}-{verb}",          # 형용사-명사-동사
        f"{abstract}-{noun}-{verb}",           # 추상명사-명사-동사
        
        # 의성어 패턴 (5개)
        f"{sound}-{noun}-{adjective}",         # 의성어-명사-형용사
        f"{adjective}-{sound}-{noun}",         # 형용사-의성어-명사
        f"{abstract}-{sound}-{adjective}",     # 추상명사-의성어-형용사
        f"{sound}-{abstract}-{noun}",          # 의성어-추상명사-명사
        f"{direction}-{sound}-{adjective}",    # 방향-의성어-형용사
        
        # 방향 패턴 (3개)
        f"{direction}-{abstract}-{verb}",      # 방향-추상명사-동사
        f"{direction}-{date}-{noun}",          # 방향-날짜-명사
        f"{direction}-{number}-{noun}",        # 방향-숫자-명사
        
        # 고유명사 패턴 (4개)
        f"{name}-{noun}-{verb}",               # 고유명사-명사-동사
        f"{noun}-{name}-{adjective}",          # 명사-고유명사-형용사
        f"{name}-{verb}-{adjective}",          # 고유명사-동사-형용사
        f"{adjective}-{name}-{noun}",          # 형용사-고유명사-명사
        
        # 날짜 패턴 (5개)
        f"{date}-{noun}-{verb}",               # 날짜-명사-동사
        f"{noun}-{date}-{adjective}",          # 명사-날짜-형용사
        f"{date}-{verb}-{adjective}",          # 날짜-동사-형용사
        f"{adjective}-{date}-{noun}",          # 형용사-날짜-명사
        f"{abstract}-{date}-{noun}",           # 추상명사-날짜-명사
        
        # 숫자 패턴 (5개)
        f"{number}-{noun}-{verb}",             # 숫자-명사-동사
        f"{noun}-{number}-{adjective}",        # 명사-숫자-형용사
        f"{number}-{verb}-{adjective}",        # 숫자-동사-형용사
        f"{adjective}-{number}-{noun}",        # 형용사-숫자-명사
        f"{abstract}-{number}-{noun}",         # 추상명사-숫자-명사
        
        # 포네틱 패턴 (4개)
        f"{phonetic}-{noun}-{verb}",           # 포네틱-명사-동사
        f"{noun}-{phonetic}-{adjective}",      # 명사-포네틱-형용사
        f"{phonetic}-{verb}-{adjective}",      # 포네틱-동사-형용사
        f"{adjective}-{phonetic}-{noun}",      # 형용사-포네틱-명사
        
        # 추가 혼합 패턴 (1개)
        f"{sound}-{date}-{noun}"               # 의성어-날짜-명사
    ]
    
    # 무작위 패턴 선택하여 소문자로 반환
    return random.choice(patterns).lower()





def check_duplicates() -> dict:
    """
    모든 카테고리에서 중복되는 단어들을 찾습니다.
    
    Returns:
        dict: 중복된 단어와 해당 카테고리들의 매핑
    """
    all_categories = {
        "NOUNS": NOUNS,
        "VERBS": VERBS, 
        "ADJECTIVES": ADJECTIVES,
        "ABSTRACTS": ABSTRACTS,
        "DIRECTIONS": DIRECTIONS,
        "SOUNDS": SOUNDS,
        "NAMES": NAMES,
        "DATES": DATES,
        "NUMBERS": NUMBERS,
        "PHONETIC": PHONETIC
    }
    
    duplicates = {}
    word_locations = {}
    
    # 모든 단어와 그 카테고리를 수집
    for category, words in all_categories.items():
        for word in words:
            if word not in word_locations:
                word_locations[word] = []
            word_locations[word].append(category)
    
    # 중복된 단어들만 필터링
    for word, categories in word_locations.items():
        if len(categories) > 1:
            duplicates[word] = categories
            
    return duplicates


def get_word_counts() -> dict:
    """
    각 카테고리별 단어 수를 반환합니다.
    
    Returns:
        dict: 카테고리별 단어 수와 패턴별 조합 수
    """
    counts = {
        "nouns": len(NOUNS),
        "verbs": len(VERBS), 
        "adjectives": len(ADJECTIVES),
        "abstracts": len(ABSTRACTS),
        "directions": len(DIRECTIONS),
        "sounds": len(SOUNDS),
        "names": len(NAMES),
        "dates": len(DATES),
        "numbers": len(NUMBERS),
        "phonetic": len(PHONETIC)
    }
    
    # 각 패턴별 조합 수 계산 (30개 패턴)
    pattern_combinations = {
        # 기본 패턴 (3개)
        "noun-verb-adj": counts["nouns"] * counts["verbs"] * counts["adjectives"],
        "adj-noun-verb": counts["adjectives"] * counts["nouns"] * counts["verbs"],
        "abstract-noun-verb": counts["abstracts"] * counts["nouns"] * counts["verbs"],
        
        # 의성어 패턴 (5개)
        "sound-noun-adj": counts["sounds"] * counts["nouns"] * counts["adjectives"],
        "adj-sound-noun": counts["adjectives"] * counts["sounds"] * counts["nouns"],
        "abstract-sound-adj": counts["abstracts"] * counts["sounds"] * counts["adjectives"],
        "sound-abstract-noun": counts["sounds"] * counts["abstracts"] * counts["nouns"],
        "direction-sound-adj": counts["directions"] * counts["sounds"] * counts["adjectives"],
        
        # 방향 패턴 (3개)
        "direction-abstract-verb": counts["directions"] * counts["abstracts"] * counts["verbs"],
        "direction-date-noun": counts["directions"] * counts["dates"] * counts["nouns"],
        "direction-number-noun": counts["directions"] * counts["numbers"] * counts["nouns"],
        
        # 고유명사 패턴 (4개)
        "name-noun-verb": counts["names"] * counts["nouns"] * counts["verbs"],
        "noun-name-adj": counts["nouns"] * counts["names"] * counts["adjectives"],
        "name-verb-adj": counts["names"] * counts["verbs"] * counts["adjectives"],
        "adj-name-noun": counts["adjectives"] * counts["names"] * counts["nouns"],
        
        # 날짜 패턴 (5개)
        "date-noun-verb": counts["dates"] * counts["nouns"] * counts["verbs"],
        "noun-date-adj": counts["nouns"] * counts["dates"] * counts["adjectives"],
        "date-verb-adj": counts["dates"] * counts["verbs"] * counts["adjectives"],
        "adj-date-noun": counts["adjectives"] * counts["dates"] * counts["nouns"],
        "abstract-date-noun": counts["abstracts"] * counts["dates"] * counts["nouns"],
        
        # 숫자 패턴 (5개)
        "number-noun-verb": counts["numbers"] * counts["nouns"] * counts["verbs"],
        "noun-number-adj": counts["nouns"] * counts["numbers"] * counts["adjectives"],
        "number-verb-adj": counts["numbers"] * counts["verbs"] * counts["adjectives"],
        "adj-number-noun": counts["adjectives"] * counts["numbers"] * counts["nouns"],
        "abstract-number-noun": counts["abstracts"] * counts["numbers"] * counts["nouns"],
        
        # 포네틱 패턴 (4개)
        "phonetic-noun-verb": counts["phonetic"] * counts["nouns"] * counts["verbs"],
        "noun-phonetic-adj": counts["nouns"] * counts["phonetic"] * counts["adjectives"],
        "phonetic-verb-adj": counts["phonetic"] * counts["verbs"] * counts["adjectives"],
        "adj-phonetic-noun": counts["adjectives"] * counts["phonetic"] * counts["nouns"],
        
        # 추가 혼합 패턴 (1개)
        "sound-date-noun": counts["sounds"] * counts["dates"] * counts["nouns"]
    }
    
    total_combinations = sum(pattern_combinations.values())
    
    return {
        **counts,
        "pattern_combinations": pattern_combinations,
        "total_combinations": total_combinations
    }


# ═══════════════════════════════════════════════════════════════
# 🧪 테스트 및 디버깅용 함수들
# ═══════════════════════════════════════════════════════════════

def generate_sample_slugs(count: int = 5, seed: int = None) -> list[str]:
    """
    샘플 slug들을 생성합니다 (테스트용).
    
    Args:
        count: 생성할 slug 개수
        seed: 테스트용 랜덤 시드 (선택적, None이면 완전 랜덤)
        
    Returns:
        list[str]: 생성된 slug 목록
    """
    if seed is not None:
        # 시드가 설정된 경우 각 slug마다 다른 시드 사용
        return [generate_slug(seed + i) for i in range(count)]
    else:
        random.seed(time.time())
        return [generate_slug() for _ in range(count)]





if __name__ == "__main__":
    # 테스트 실행
    print("=== 확장된 Slug Generator Test ===")
    
    # 중복 검사 먼저 실행
    duplicates = check_duplicates()
    if duplicates:
        print(f"\n⚠️  중복 단어 발견:")
        for word, categories in duplicates.items():
            print(f"   '{word}' → {', '.join(categories)}")
    else:
        print(f"\n✅ 중복 단어 없음: 모든 카테고리의 단어가 고유합니다.")
    
    # 단어 통계 출력
    stats = get_word_counts()
    print(f"\n📊 단어 통계:")
    print(f"   명사: {stats['nouns']}개 (동물 34 + 자연 32 + 음식 24 + 물건 27), 동사: {stats['verbs']}개 (기본동작 46 + 감정상태 24 + 창작 5 + 개발 20)")
    print(f"   형용사: {stats['adjectives']}개 (특성 38 + 색깔 18 + 크기 19), 추상명사: {stats['abstracts']}개 (class 포함)")
    print(f"   방향: {stats['directions']}개, 의성어: {stats['sounds']}개, 고유명사: {stats['names']}개 (도시 22 + 이름 30)")
    print(f"   날짜: {stats['dates']}개 (월 12 + 요일 7), 숫자: {stats['numbers']}개, 포네틱: {stats['phonetic']}개")
    print(f"   총 조합 수: {stats['total_combinations']:,}개")
    
    print("\n🎨 랜덤 slug 샘플들 (30가지 패턴 혼합):")
    samples = generate_sample_slugs(10, seed=42)
    for i, slug in enumerate(samples, 1):
        print(f"   {i:2d}. {slug}")
    
    print("\n🎲 완전 랜덤 (seed 없음):")
    random_samples = generate_sample_slugs(10)
    for i, slug in enumerate(random_samples, 1):
        print(f"   {i}. {slug}") 