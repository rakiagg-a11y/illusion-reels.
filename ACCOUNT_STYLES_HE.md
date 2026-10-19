# שיוך הגנרטורים שאושר ב־19.10.2026

| עמוד | המסלול הפעיל כעת | אופי השינוי |
|---|---|---|
| `@hypnotorium` | **ColorEcho** (`color_echo`) + **FaceFlash** (`face_flash`) | מחליפים את MotionShift; `motion_form`, `infinite_regress`, `footsteps` אינם מצבי ברירת המחדל של העמוד |
| `@spiralium_` | **MirrorFlip** (`mirror_flip`) + **StillWobble** (`still_wobble`) | מחליפים את StereoTwin; `helix`, `orbital_rings`, `constellation` אינם מצבי ברירת המחדל של העמוד |
| `@opticpop` | **AngleSpin** הקיים: `bistable_spin`, `tilted_pair`, ובנוסף **DepthFlip** (`depth_flip`) | תוספת; שני המצבים הקיימים משתמשים בדיוק במנוע הציור הקודם |

TrustYourEyes מחוץ לשינוי הזה. אין שינוי ב־`generators/perception_lab.py`,
`five_styles.py`, `five_style_render.py`, `pointcloud.py` או בנכסי/קוד Brainrot של קלאוד.
אין שינוי בחיבורים, פרסום, תזמונים, סאונד, Metricool, OmniSocials או main.

## הפעלה מקומית

אותם Python, NumPy, Pillow, SciPy ו־FFmpeg של הפרויקט. Blender אינו נדרש.

```powershell
python -m pip install -r requirements-creative.txt
python generators/hypnotorium.py --out local_demo/hypno_01 --mode color_echo --seed 42
python generators/spiralium.py --out local_demo/spiral_01 --mode still_wobble --seed 43
python generators/opticpop.py --out local_demo/optic_01 --mode depth_flip --seed 44
```

אם FFmpeg אינו ב־PATH, מוסיפים `--ffmpeg "C:/path/to/ffmpeg.exe"`.
ברירת המחדל היא 1080×1920, ‏30fps. אפשר להוסיף `--preview` לדגימה 360×640, ‏15fps.
ב־FaceFlash איכות מלאה חשובה: ב־30fps תמונה של 250ms מוחזקת לסירוגין במשך 7/8 פריימים;
הטיימינג הרציף נשאר 4 זוגות בשנייה, ללא מסך הבהוב או עיוות פנים מצויר.

גם קיצורי ההפעלה הקיימים `generators/motion_paradox.py` ו־`generators/binocular_worlds.py`
מפנים כעת לשיוך החדש. `generators/reversible_depth.py` מציע את שני מצבי OpticPop הקיימים
וגם DepthFlip. אין צורך לזכור שם חדש כדי שההחלפה תחול. בחירת מצב ישן של Hypno/Spiral נדחית.

ללא `--mode`, ההיסטוריה מאזנת בין המצבים המאושרים, גם בהפעלות נפרדות.
שישה תדריכים חדשים עבור Hypno/Spiral יתפצלו לשלושה מכל סגנון; OpticPop מתחלק בין שלושת מצביו.
זה אינו יוצר לוח פרסום. ההיסטוריה כברירת מחדל נשארת
`local_demo/ready_generators_history.json`; להעברת היסטוריה קיימת משתמשים ב־`--history` עם אותו קובץ.
אין איחוד אוטומטי של היסטוריות, ולכן להפעלת ייצור משתמשים תמיד בנתיב מוסכם אחד.

## תדריכים לקלאוד ודוגמאות

```powershell
python account_studio.py --account hypnotorium --plan --count 6 --seed 42 --out local_demo/hypno_plan.json
python account_studio.py --account spiralium_ --plan --count 6 --seed 43 --out local_demo/spiral_plan.json
python demo_accounts.py --out local_demo/account_review --ffmpeg "C:/path/to/ffmpeg.exe"
```

התוכנית מכילה `briefs`, אחד לכל סרטון, עם עמוד, מצב, פרמטרים, כיתוב, עקרון תפיסתי,
בקרת מנגנון, מקור ההשראה והגדרות רינדור. `publishing_allowed` תמיד false;
הדירוג הוא רשימת בדיקה הנדסית, ואינו חיזוי הצלחה. תוכנית בלבד אינה שומרת מקומות בהיסטוריה:
יש להפיק תדריך ולרנדר בהיסטוריה המשותפת, או לוודא אי־כפילות לפני ביצוע תוכניות מקבילות.

כדי לרנדר תדריך מתוך תוכנית, שומרים את אובייקט התדריך הבודד כ־JSON ומעבירים ל־`--brief`:

```powershell
python generators/hypnotorium.py --brief local_demo/reviewed_brief.json --out local_demo/hypno_full --history local_demo/ready_generators_history.json
```

קידום preview לאיכות מלאה מחייב אותו תדריך בדיוק, אותה היסטוריה וקובץ preview תקין.
OpticPop מקבל גם תדריכי `five_style_production_brief` קודמים דרך אותו `--brief`, ללא עטיפה או שינוי החתימה.
היסטוריה ננעלת בזמן רינדור; לא נרשם סרטון שנכשל בקידוד, ותוצר קיים אינו נדרס.
יש קטלוגים סופיים: 120 סצנות ColorEcho, ‏120 חפיסות FaceFlash, ‏100 קומפוזיציות MirrorFlip,
240 טקסטורות StillWobble ו־144 מעטפות DepthFlip. שינוי צבע או seed בלבד אינו מבנה חדש.
יש מספיק לשני המצבים של Hypno/Spiral ל־31 יום × 6 סרטונים (93 מכל סגנון); אין הבטחה לגיוון אינסופי.

ממשקי `five_styles.py` ותיקיית `samples/five_styles/` הם חוזי עבר לשחזור תדריכים שכבר הופקו.
אין להשתמש ב־`five_styles.py init/plan` לשיוך החדש: הוא עדיין מתאר חמישה פרופילים עם סגנון אחד לכל פרופיל.
המסלול החדש הוא `account_studio.py`, וקובצי ההפעלה המפורטים כאן.
`generate.py` ו־RUNBOOK נשארים במסלול הפרסום ההיסטורי; לא הופעל חיבור בין המסלול החדש לתור חי.

## מה האשליות עושות בפועל

- **ColorEcho:** אותה סצנה מקורית, 18 שניות הסתגלות לצבע משלים ואז 6 שניות תמונה אפורה בפועל.
  הסימון והגאומטריה נשארים במקום; אפשר לייצא בקרת הסתגלות אפורה באמצעות `control_frame(t)`.
  הקידוד מכריח פריים מפתח בשנייה 18 כדי למנוע משאריות צבע של שלב ההסתגלות להישאר בחיזוי הדחיסה.
- **FaceFlash:** זוגות פנים מאוירים מקוריים עם מיקום עיניים קבוע, מתחלפים כל 250ms.
  לא מצויר עיוות. יש בקרת פער של 250ms. נדרש לבדוק אם האפקט חזק דיו באיורים לפני פרסום.
- **MirrorFlip:** שני פרופילים מול אגרטל — אותו גבול מגדיר שתי קריאות; מוצג גם עותק בהשתקפות מדויקת.
  זהו אנלוג Rubin מקורי. אינו שכפול של ציור Ocampo ואינו הוכחה שהשתקפות לבדה יוצרת אשליה.
- **StillWobble:** טקסטורת Ouchi מקורית עם כיוונים ניצבים במרכז וברקע.
  כל פריימי המקור זהים. תנועת צפייה קלה עשויה ליצור תנועה נתפסת; בקרת כיוון אחיד זמינה.
  אין טענה שהוכח המנגנון המדויק של רפרנס הכמהין.
- **DepthFlip:** מעטפת קשת שקופה, סיבוב רציף בהיטל אורתוגרפי ללא הסתרות/הצללת עומק.
  השתקפות עומק עם סיבוב והטיה הפוכים נותנת אותן נקודות דו־ממדיות. אין היפוך כיוון מתוכנת.

יש לבדוק את הווידאו המקודד בגודל טלפון, לא רק תמונת קוד. הבדיקות מאמתות תנאים פיזיקליים;
הן אינן מוכיחות שצופה מסוים יחווה את האשליה. קידוד H.264 עשוי לשנות פרטים, במיוחד בטקסטורות צפופות.

## הבסיס המספרי וגבולותיו

610 מתוך 611 קישורי Reel שמופו קודם נמדדו ב־19.10.2026. שיתופים לא היו זמינים לציבור;
אין דירוג מוכח לפי לייקים+תגובות+שיתופים, ולא נבדק כל פוסט בחשבון. נבחרו דוגמאות שיא
למשפחות מנגנון, ולא ממוצעי ביצועים שמוכיחים חזרתיות. המספרים מעוגלים ומצטברים:

| סגנון | דוגמה | לייקים | תגובות |
|---|---|---:|---:|
| DepthFlip | [DebEtM_uAdj](https://www.instagram.com/biologistmichael/reel/DebEtM_uAdj/) | 3.9M | 29.5K |
| MirrorFlip | [DKanwbnS2JR](https://www.instagram.com/biologistmichael/reel/DKanwbnS2JR/) | 3.5M | 12.2K |
| ColorEcho | [C-MtvEAx5mF](https://www.instagram.com/biologistmichael/reel/C-MtvEAx5mF/) | 2.4M | 18.8K |
| FaceFlash | [DFrbrWMxBB6](https://www.instagram.com/biologistmichael/reel/DFrbrWMxBB6/) | 1.7M | 14.4K |
| StillWobble | [DNEnh7iScpb](https://www.instagram.com/biologistmichael/reel/DNEnh7iScpb/) | 551.6K | 5.3K |

הצפייה ב־C-MtvEAx5mF אישרה את סיווג האשליה שהיה זמני במחקר הקודם.
לא מועתקים סרטוני מקור, תמונות פנים או יצירות אמנות. נכסי הווידאו החדשים פרוצדורליים ומקוריים.
מקורות עקרוניים: [Flashed Face Distortion, Tangen et al.](https://www.tangenlab.com/pdf/tangen_2011_flashed_face_distortion.pdf),
[מחקר Ouchi](https://www.sciencedirect.com/science/article/pii/S0042698999001625).

## בדיקות

```powershell
python -m unittest discover -s tests -v
```

קובצי TrustYourEyes והליבה המשותפת צריכים להישאר זהים לבסיס הענף; אפשר לבדוק זאת ב־Git diff.
יש לאשר את חמש הדוגמאות חזותית לפני מיזוג, ורק אחר כך לחבר תור הפקה ותזמון בנפרד.
