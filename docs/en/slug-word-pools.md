# Slug Word Pools (Friendly Slug Generator)

Friendly auto-generated slugs are built from categorized word lists stored in repo-tracked txt files:
* `app/core/data/slug_words/noun.txt`
* `app/core/data/slug_words/verb.txt`
* `app/core/data/slug_words/adjective.txt`
* `app/core/data/slug_words/abstract.txt`
* `app/core/data/slug_words/direction.txt`
* `app/core/data/slug_words/sound.txt`
* `app/core/data/slug_words/name.txt`
* `app/core/data/slug_words/date.txt`
* `app/core/data/slug_words/number.txt`
* `app/core/data/slug_words/phonetic.txt`

TXT rules:
* One word per line (UTF-8)
* Blank lines ignored
* Lines starting with `#` are comments
* Words are normalized to lowercase and must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`

Settings:
* `SLUG_WORDS_FILES_ENABLED=true` (default)
* `SLUG_WORDS_FILES_DIR=app/core/data/slug_words` (project-root relative by default)

Behavior:
* Word files are loaded once at startup (restart server after editing files).
* If `SLUG_WORDS_FILES_ENABLED=false`, friendly slug generation is disabled and UUID hex values are used.
* If loading fails, the server still starts and auto-generated slugs fall back to UUID hex values.
