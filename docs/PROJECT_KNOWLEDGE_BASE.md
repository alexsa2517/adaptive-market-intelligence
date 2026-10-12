# บันทึกความรู้โครงการ AI Crypto / Adaptive Market Intelligence

> อัปเดตบันทึก: 2026-10-12  
> หลักการสูงสุด: **PROVE BEFORE TRADE** — ต้องพิสูจน์ด้วยข้อมูลที่ไม่รั่วไหล การทดสอบนอกตัวอย่าง ความทนทานต่อต้นทุน และ Paper Trading ก่อนพิจารณาเงินจริง  
> เอกสารนี้เป็นบันทึกความรู้/แผนงาน ไม่ใช่คำรับรองผลตอบแทนหรือคำแนะนำการลงทุน

## 1. เป้าหมาย

พัฒนาระบบ AI วิเคราะห์ตลาดคริปโตและช่วยตัดสินใจอย่างเป็นระบบ โดยเริ่มจาก BTC และสามารถขยายไปยังเหรียญอื่นได้ เป้าหมายระยะยาวคือระบบ Market Intelligence ที่รวม:
- ข้อมูลราคาและปริมาณซื้อขาย
- Technical features และ market regimes
- การพยากรณ์หลายช่วงเวลา
- ข่าว ความเชื่อมั่น และข้อมูลเศรษฐกิจมหภาค
- On-chain metrics เมื่อมีแหล่งข้อมูลที่เหมาะสม
- การตรวจจับความผิดปกติและระบบเตือนความเสี่ยง
- การเปรียบเทียบโมเดลและ AI Router ที่เลือกโมเดลจากหลักฐาน
- Backtest, walk-forward validation, paper trading และรายงานผลที่ทำซ้ำได้

ระบบต้องมีสิทธิ์เลือก **NO TRADE** เมื่อหลักฐานไม่เพียงพอ ห้ามบังคับให้มีสัญญาณซื้อหรือขายตลอดเวลา และไม่ใช้ LLM ตัดสินใจซื้อขายโดยตรงโดยไม่มีกรอบความเสี่ยงและการทดสอบ

## 2. แหล่งเก็บงานและสภาพแวดล้อม

### GitHub หลัก
- Repository: https://github.com/alexsa2517/adaptive-market-intelligence
- GitHub เป็นแหล่งเก็บโค้ดและประวัติการเปลี่ยนแปลงหลัก
- ใช้ Google Colab สำหรับงานทดลองที่ต้องใช้ทรัพยากรหรือรันซ้ำ
- เก็บ API keys และ secrets ใน environment variables หรือ Colab Secrets เท่านั้น ห้าม commit ลง GitHub

### บอททดลองในเครื่อง
- โฟลเดอร์ที่ใช้งาน: `C:\Users\lexso\Desktop\bitkub_bot`
- สภาพแวดล้อมที่เคยตรวจสอบ: Windows, Python 3.11, pandas 2.3.3, ccxt 4.5.30
- บอททดลองในโฟลเดอร์นี้ยังต้องตรวจสอบการเชื่อมต่อ exchange และความถูกต้องของข้อมูลก่อนใช้งานจริง
- อย่าสันนิษฐานว่า `ccxt.bitkub()` ใช้งานได้ในเวอร์ชันที่ติดตั้ง จนกว่าจะตรวจสอบ exchange support และทดสอบอย่างชัดเจน
- ปัจจุบันยังไม่มีเงินจริงสำหรับทดสอบ จึงใช้เฉพาะข้อมูลสาธารณะ, backtest และ paper trading

> หมายเหตุ: บอทในเครื่องกับ repository นี้อาจเป็นคนละชุดการทดลอง ต้องระบุให้ชัดว่าผลทดสอบมาจากระบบใด ห้ามนำผลของระบบหนึ่งไปอ้างเป็นผลของอีกระบบหนึ่ง

## 3. สถานะหลักฐานของงานวิจัยใน repository

README ของ repository บันทึกสถานะ V1.12 Forward Validation ไว้ดังนี้:
- โมเดลวิจัยที่ล็อกไว้: XGBoost สำหรับทิศทาง BTC รายวัน
- Feature Set C และ Moderate market-regime filter
- ช่วงฝึกที่ล็อก: 2021-07-23 ถึง 2024-11-03 (1,200 แถว)
- Probability threshold: 0.60
- ต้นทุนฐาน: ค่าธรรมเนียม 0.10% + slippage 0.05% ต่อการเปลี่ยนสถานะ
- ผล final holdout ที่ README บันทึกสำหรับช่วง 2026-05-08 ถึง 2026-09-04: ผลตอบแทน +20.43%, max drawdown -1.97%, Sharpe 3.09 และ profit factor 5.61 ภายใต้สมมติฐานต้นทุนฐาน
- ผล robustness V1.11 ถูกจัดเป็น **PROMISING — MORE VALIDATION REQUIRED** ไม่ใช่ผลที่พิสูจน์แล้ว จุดอ่อนที่บันทึกไว้คือจำนวนวันที่มีสถานะจริงน้อยและการทดสอบ outlier ไม่ผ่าน
- Forward observations ที่ README บันทึก: 2026-09-05 และ 2026-09-07 ไม่มีสัญญาณ เพราะ `prob_up` ต่ำกว่า 0.60

ตัวเลขข้างต้นเป็นข้อมูลที่บันทึกไว้ใน README ของ repository ณ วันที่จัดทำเอกสารนี้ ไม่ใช่การรับรองว่าโมเดลจะทำกำไรในอนาคต และต้องรักษา holdout/forward data ให้แยกจากการฝึกและการปรับพารามิเตอร์

## 4. สถานะบอททดลองในเครื่อง (bitkub_bot)

การทดลองล่าสุดที่มีบันทึก:
- ใช้ข้อมูล OHLCV BTC/USDT จาก Binance public market data เป็นแหล่งข้อมูลทดลอง
- สคริปต์ที่เกี่ยวข้อง: `fetch_binance.py`, `train_ai.py`
- ไฟล์ข้อมูล: `data.csv`
- ไฟล์โมเดล: `ai_model.pkl`
- เคยใช้ข้อมูลได้เพียง 1,000 แท่ง แม้ตั้งเป้าดึง 10,000 แท่ง เพราะ pagination รุ่นก่อนมีปัญหา
- มีการเสนอให้เปลี่ยนตัวดึงข้อมูลเป็น Binance REST klines endpoint และแบ่งดึงย้อนหลังโดยใช้ `endTime` แต่จำนวนแถวหลังรันเวอร์ชันใหม่นั้นยังไม่ได้รับการยืนยันในบันทึกล่าสุด
- โครงสร้างคอลัมน์เคยเป็น `time/open/high/low/close/volume`; สคริปต์ใหม่อาจใช้ `timestamp/open/high/low/close/volume` จึงต้องตรวจสอบให้ตรงกับโค้ดฝึกโมเดล
- `train_ai.py` สร้าง features เช่น returns, EMA, RSI, ATR, MACD, volume change/spike และตั้ง target ว่าราคาปิดในอีก 5 แท่งสูงกว่าราคาปัจจุบันหรือไม่
- แบ่ง train/test ตามลำดับเวลา ไม่สุ่มสลับข้อมูล
- ผลรันล่าสุดที่ยืนยันได้จากข้อมูล 1,000 แถว: หลังคำนวณ indicators/target เหลือ 976 แถว, train 780, test 196 และ Accuracy = 0.4541
- Accuracy 0.4541 ยังไม่แสดง edge ที่น่าเชื่อถือ และห้ามนำไปใช้เทรดเงินจริง

ผลจากบอททดลองนี้เป็นคนละการทดลองกับผล V1.12 ใน repository จนกว่าจะพิสูจน์ว่าใช้ข้อมูล โมเดล กฎกลยุทธ์ และขั้นตอนเดียวกัน

## 5. ข้อกำหนดข้อมูลและการฝึกโมเดล

1. ใช้ข้อมูลตามเวลาและรักษาลำดับเวลา ห้ามสุ่มแบ่งข้อมูล time series แบบทั่วไป
2. ป้องกัน look-ahead/data leakage: feature ณ เวลาทำนายต้องไม่ใช้ข้อมูลอนาคต
3. ตรวจ timestamp ซ้ำ ข้อมูลขาดหาย ลำดับเวลา OHLCV ผิดปกติ และค่าที่ไม่ใช่ตัวเลข
4. บันทึกจำนวนแถวก่อนและหลัง cleaning, ช่วงเวลาเริ่ม/สิ้นสุด และแหล่งข้อมูลทุกครั้ง
5. ตรวจ label ที่ยังไม่ทราบผลให้เป็น missing และตัดออกอย่างถูกต้อง ห้ามเปลี่ยนเป็น class 0 โดยอัตโนมัติ
6. ทำ baseline comparison ก่อนตีความ accuracy เช่น majority-class baseline
7. รายงานอย่างน้อย confusion matrix, precision/recall, balanced accuracy, ROC-AUC เมื่อเหมาะสม และผลแยกตาม regime
8. ประเมินด้วย chronological holdout, walk-forward validation และ untouched final holdout
9. อย่าเลือกโมเดลจาก training accuracy หรือจากการทดลองครั้งเดียว
10. เก็บ configuration, random seed, data window, feature list, dependency versions และผลการทดลองเพื่อทำซ้ำได้

## 6. Backtest ที่สมจริง

Backtest ต้องคิดต้นทุนและกติกาที่เกิดขึ้นจริง ไม่ใช่ดู accuracy อย่างเดียว:
- Trading fee และ slippage; เริ่มจากสมมติฐานฐาน 0.10% + 0.05% ต่อการเปลี่ยนสถานะตามการวิจัยใน repository แล้วทำ cost sensitivity เพิ่ม
- Position sizing, cash balance, exposure limits และจำนวนสถานะสูงสุด
- Stop-loss/take-profit หากใช้ ต้องทดสอบตามลำดับข้อมูลจริงและไม่ใช้ราคาที่อนาคตทราบแล้ว
- ป้องกันการนับผลตอบแทนซ้ำและตรวจหน่วยเปอร์เซ็นต์/ทศนิยม
- รายงาน net return หลังต้นทุน, max drawdown, Sharpe/Sortino เมื่อเหมาะสม, profit factor, win rate, จำนวน trades, exposure/turnover และช่วงที่ขาดทุนหนัก
- เปรียบเทียบกับ buy-and-hold และ baseline ที่เรียบง่าย
- ทำ stress test: ค่าธรรมเนียมสูงขึ้น, slippage สูงขึ้น, latency/ข้อมูลหาย, regime เปลี่ยน และ block bootstrap เมื่อเหมาะสม
- ถ้าผลไม่ผ่าน ให้กลับไปวิจัยหรือ NO TRADE ไม่ปรับพารามิเตอร์จาก holdout เพื่อบังคับให้ผลดีขึ้น

## 7. Roadmap ที่บันทึกไว้

1. ตรวจและยืนยันคุณภาพข้อมูล OHLCV และ pagination ให้ดึงได้ครบตามจำนวนที่ตั้งไว้
2. ทำ baseline ที่ทำซ้ำได้และเปรียบเทียบกับ baseline ง่าย ๆ
3. ทำ backtest หลังต้นทุน พร้อมรายงานความเสี่ยงและจำนวน trades
4. ทำ walk-forward, cost sensitivity, regime analysis และ stress test
5. แยก V2 research track สำหรับข้อมูลภายนอก โดยไม่แก้ไขโมเดล V1.12 ที่ล็อกไว้
6. ทดลอง Market + Macro, Market + News และ Market + Macro + News ตามลำดับ
7. เพิ่ม multi-horizon forecasts, sentiment/NLP, on-chain, anomaly/early warning และ ensemble/router เฉพาะเมื่อข้อมูลและหลักฐานพร้อม
8. สร้าง paper trading ที่บันทึกสัญญาณ ราคา ณ เวลานั้น เหตุผล สถานะพอร์ต ต้นทุนจำลอง และผลที่เกิดขึ้นจริง
9. ประเมินความเสถียรในหลายสภาวะตลาดและหลายช่วงเวลา
10. พิจารณา live-trading gate แยกต่างหาก หลังผ่านเกณฑ์ที่กำหนดไว้ล่วงหน้าเท่านั้น

## 8. เกณฑ์ก่อนพิจารณาเงินจริง

ห้ามเชื่อมระบบให้ส่งคำสั่งเงินจริง จนกว่าจะมีหลักฐานที่ทำซ้ำได้ว่า:
- ผ่านการตรวจสอบข้อมูลและ leakage audit
- ผ่าน walk-forward และ untouched holdout โดยไม่มีการปรับกฎย้อนหลังตามผล holdout
- ผลสุทธิยังสมเหตุสมผลหลังค่าธรรมเนียมและ slippage ที่สมจริง
- ผ่าน stress tests และมี drawdown/position limits ที่ชัดเจน
- paper trading ทำงานต่อเนื่องและผลสอดคล้องกับสมมติฐาน
- มี kill switch, logging, error handling และการจัดการกรณี API ล้มเหลว
- API keys ถูกเก็บเป็นความลับและใช้สิทธิ์เท่าที่จำเป็น; ห้ามเปิดสิทธิ์ถอนเงินให้บอท
- ผู้ใช้ตรวจสอบและอนุมัติความเสี่ยงก่อนเปิด live trading

การผ่านเกณฑ์เหล่านี้ไม่ได้รับประกันกำไร แต่ช่วยลดความเสี่ยงจากข้อผิดพลาดและการสรุปผลเกินหลักฐาน

## 9. ข้อควรระวังทางเทคนิคที่พบ

- `pandas_ta` ติดตั้งไม่สำเร็จในสภาพแวดล้อม Python 3.11 ที่เคยใช้ จึงคำนวณ indicators ด้วย pandas/numpy หรือใช้ไลบรารีที่ตรวจสอบ compatibility แล้ว
- `ccxt` เวอร์ชัน 4.5.30 เคยมีปัญหาเรื่องการเรียก `ccxt.bitkub`; ตรวจรายชื่อ exchange ที่รองรับในเวอร์ชันที่ติดตั้งก่อนใช้งาน
- การดึงข้อมูล 1,000 แถวไม่ได้แปลว่าระบบดึงข้อมูลครบ ต้องตรวจจำนวนแถวจริงและช่วง timestamp
- ระวัง mismatch ระหว่างชื่อคอลัมน์ `time` กับ `timestamp`
- ระวัง position sizing ที่ทำให้ขนาดคำสั่งเล็กจนผล PnL เป็นศูนย์หรือหน่วยเงินไม่ตรงกัน
- เคยมี backtest ทดลองที่ขาดทุน: เงินเริ่มต้น 1,000, เงินสุดท้าย 842.35, Net PnL -157.65 จึงต้องตรวจ logic และไม่เลือกเฉพาะผลที่ดูดี
- สคริปต์ที่มี SyntaxError หรือถูกตัดไม่ครบต้องแก้ให้เป็นไฟล์สมบูรณ์ แล้วรันตรวจ syntax/test ก่อนใช้ผล
- ห้าม commit API keys, tokens, passwords หรือไฟล์ `.env` ลง repository หากเคยเปิดเผย token ให้เพิกถอนและออกใหม่

## 10. รูปแบบการบันทึกการทดลอง

สำหรับแต่ละการทดลองให้บันทึก:
- Experiment ID / วันที่
- Commit SHA หรือเวอร์ชันโค้ด
- แหล่งข้อมูลและ timeframe
- ช่วงข้อมูล train/validation/test/forward
- จำนวนแถวและวิธี cleaning
- Features, target, model และ hyperparameters
- ต้นทุนและกฎ position sizing
- Baseline metrics และ net backtest metrics
- Robustness/stress-test results
- ข้อสรุป: FAIL / INCONCLUSIVE / PROMISING — MORE VALIDATION REQUIRED / PASS FOR PAPER ONLY
- ข้อจำกัดและการทดลองถัดไป

## 11. หลักการทำงานร่วมกัน

- แก้ต่อจากของเดิม ไม่สร้างโปรเจกต์ใหม่หรือรื้อระบบโดยไม่จำเป็น
- ก่อนแก้ไฟล์สำคัญ ให้ตรวจสถานะ repository และเนื้อหาเดิม
- เปลี่ยนทีละส่วน พร้อมอธิบายไฟล์ที่เปลี่ยนและคำสั่งตรวจสอบ
- ให้คำสั่งที่รันได้จริงบน Windows/Google Colab และส่งไฟล์โค้ดให้ครบ ไม่ตัดกลางบล็อก
- แยกข้อเท็จจริงที่วัดได้ออกจากสมมติฐานและแผนในอนาคต
- ไม่อ้างว่าระบบทำกำไรแน่นอน และไม่ใช้เงินจริงก่อนผ่านขั้นตอนพิสูจน์

## 12. แหล่งเอกสารที่ควรอ่านต่อ

- Repository README: [README.md](../README.md)
- V2 feature specification: [docs/v2_feature_spec.md](v2_feature_spec.md)
- V1 baseline notebook: [notebooks/01_v1_baseline.ipynb](../notebooks/01_v1_baseline.ipynb)
- V2 external-data research scaffold: [notebooks/04_v2_external_data_research.py](../notebooks/04_v2_external_data_research.py)

---
เอกสารนี้ควรอัปเดตเมื่อมีผลทดสอบใหม่ที่ยืนยันได้ โดยไม่เขียนทับหรือทำให้ผลวิจัยที่ล็อกไว้สูญเสียความสามารถในการตรวจสอบย้อนหลัง
