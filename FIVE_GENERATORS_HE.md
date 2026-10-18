# חמישה גנרטורים נפרדים להפעלה

לכל סגנון יש כעת קובץ הפעלה משלו. אפשר לייצר סרטון מסגנון אחד בלי להפעיל
את ארבעת האחרים. הגנרטורים חולקים את ליבת הציור, הבדיקות וההיסטוריה;
אלה חמישה מסלולי יצירה פרוצדורליים, לא חמישה מודלי AI שאומנו בנפרד.

| מספר | גנרטור | קובץ הפעלה | דוגמת הסרטון החדשה |
|---|---|---|---|
| 1 | אובייקטים מסתובבים בזוויות | `generators/reversible_depth.py` | לב ופרפר |
| 2 | סטריאוגרמה עם עומק חבוי | `generators/hidden_stereogram.py` | כוכב חבוי |
| 3 | שתי נקודות מבט לעולם מרחבי | `generators/binocular_worlds.py` | סליל |
| 4 | צורות ופרדוקסים של תנועה | `generators/motion_paradox.py` | ברק בתוך רעש נע |
| 5 | ניסויי צבע, גודל והקשר | `generators/perception_lab.py` | שתי שורות באורך שווה |

## יצירת סרטון אחד

נדרשים אותם Python, numpy, Pillow, scipy ו־FFmpeg של הפרויקט הקיים.
מתוך תיקיית הפרויקט, למשל:

```powershell
python generators/reversible_depth.py --out work/rotating_01 --seed 42 --ffmpeg "C:/path/to/ffmpeg.exe"
python generators/hidden_stereogram.py --out work/hidden_01 --seed 43 --ffmpeg "C:/path/to/ffmpeg.exe"
python generators/binocular_worlds.py --out work/stereo_01 --mode helix --ffmpeg "C:/path/to/ffmpeg.exe"
python generators/motion_paradox.py --out work/motion_01 --mode motion_form --ffmpeg "C:/path/to/ffmpeg.exe"
python generators/perception_lab.py --out work/perception_01 --mode muller_lyer --ffmpeg "C:/path/to/ffmpeg.exe"
```

מחליפים את נתיב FFmpeg בנתיב האמיתי. במחשב הפיתוח הנוכחי ניתן להשתמש
ב־`local_demo/encoder/ffmpeg.exe`. אם הוא זמין ב־PATH, אפשר להשמיט את
`--ffmpeg`. אם `python` אינו זמין בפקודה קצרה, משתמשים בנתיב ההתקנה המלא.

ברירת המחדל היא Full HD, ‏1080×1920 ב־30 פריימים לשנייה. `--preview`
מפיק תצוגה קטנה. `--handle @yourpage` משנה את הכיתוב של החשבון.
בלי `--seed` נבחר זרע חדש. כשלא בוחרים `--mode`, נבחר מצב יצירה שעדיין
יש לו מועמדים ושקיבל פחות תוצרים בהיסטוריה המקומית.

הפלט כולל MP4, תמונה, תדריך JSON וקובץ manifest. משתמשים בכל פעם בתיקיית
פלט חדשה. ההיסטוריה המשותפת לחמשת קובצי ההפעלה נמצאת כברירת מחדל ב־
`local_demo/ready_generators_history.json`; אפשר לבחור קובץ אחר עם
`--history`. היא אינה מייבאת אוטומטית היסטוריות ישנות. שינוי זרע, צבע או
חשבון בלבד לא נחשב למבנה חדש. הקטלוג סופי.

## מעבר מתצוגה קטנה לאיכות מלאה

אחרי תצוגה קטנה, מעבירים ל־`--brief` את תדריך ה־JSON שנוצר בתיקיית הפלט:

```powershell
python generators/motion_paradox.py --brief work/motion_preview/brand_04_CONCEPT.json --out work/motion_full --ffmpeg "C:/path/to/ffmpeg.exe"
```

מחליפים את שם קובץ התדריך בשם האמיתי. אין לשנות אותו או להוסיף הגדרות
כמו seed/handle בעת הקידום. בדיקת החתימה מאמתת שזהו אותו תדריך ושקובץ
התצוגה לא השתנה. משתמשים באותה היסטוריה בשני השלבים.

בחבילה עצמאית של גנרטור, קובץ ההפעלה הוא `generate.py` בשורש החבילה;
שאר האפשרויות זהות. כל חבילה כוללת את קוד הליבה הדרוש, ולכן אפשר לחלץ
רק גנרטור אחד ולהפעיל אותו בנפרד. הספריות ו־FFmpeg מותקנים במחשב ואינם
מועתקים לתוך חבילת המקור.

לבדיקת איכות האשליה יש לצפות בסרטונים עצמם בטלפון. סטריאוגרמות דורשות
הוראת צפייה מתאימה, ואשליות תנועה דורשות ניגון. אין במסלולים האלה גישה
לשירותי פרסום, תזמון או חשבונות חיצוניים.
