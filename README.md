# Hướng dẫn train mô hình Employment trên Amazon SageMaker Console

Tài liệu này hướng dẫn train model dự đoán khả năng có việc làm (`employed`) từ folder dữ liệu `../training-course-data`, **chỉ dùng giao diện AWS Console/SageMaker Canvas**. Không cần AWS CLI, terminal, hoặc lệnh deploy.

> Dự án này độc lập với các dự án khác trong workspace. Source code tại `src/` và `scripts/` là phương án tự động hóa tùy chọn; luồng chính của tài liệu này thực hiện hoàn toàn bằng giao diện AWS.

## Mục tiêu

Sau khi hoàn thành, bạn sẽ có:

1. Một dataset đã ghép và làm sạch trong Amazon S3.
2. Một Canvas model phân loại nhị phân dự đoán `employed` (`0` hoặc `1`).
3. Báo cáo chất lượng model: AUC, F1, precision, recall và accuracy.
4. Tùy chọn: SageMaker realtime endpoint để ứng dụng khác gọi dự đoán.

## Kiến trúc

```text
training-course-data (6 file)
       ↓
S3 /raw (CSV)
       ↓
SageMaker Canvas Data Wrangler (join + làm sạch)
       ↓
S3 /processed/employment_train.csv
       ↓
SageMaker Canvas (Standard build)
       ↓
Canvas model → tùy chọn deploy SageMaker endpoint
```

## 1. Dữ liệu nguồn

Folder nguồn là `../training-course-data` và chứa sáu bảng:

| File nguồn | Vai trò | Khóa |
|---|---|---|
| `Enrollies.xlsx` | Hồ sơ cơ bản: city, gender, trường học | `enrollee_id` |
| `enrollies_education.xlsx` | Trình độ/chuyên ngành | `enrollee_id` |
| `work_experience.csv` | Kinh nghiệm làm việc | `enrollee_id` |
| `training_hours.csv` | Số giờ học | `enrollee_id` |
| `city_dev_index.csv` | Chỉ số phát triển thành phố | `city` |
| `employment.csv` | Nhãn cần dự đoán: `employed` | `enrollee_id` |

Canvas không nhận file Excel (`.xlsx`) để train tabular data; input hợp lệ là CSV hoặc Parquet. Vì vậy, cần chuyển hai file Excel thành CSV trước.

### Chuyển Excel thành CSV, không dùng lệnh

Trên máy local, mở từng file bằng Microsoft Excel hoặc Numbers:

1. Mở `Enrollies.xlsx`.
2. Chọn **File → Save As**.
3. Chọn định dạng **CSV UTF-8 (Comma delimited) (.csv)**.
4. Lưu với tên `enrollies.csv`.
5. Làm tương tự với `enrollies_education.xlsx`, lưu thành `enrollies_education.csv`.

Không thay đổi tên cột khi chuyển file. Đặc biệt, giữ nguyên tên `relevent_experience` (lỗi chính tả này có trong dữ liệu nguồn và sẽ được dùng xuyên suốt pipeline).

## 2. Chuẩn bị AWS Console

### Chọn Region

Chọn một Region và dùng duy nhất Region đó cho S3, SageMaker Studio và Canvas. Có thể dùng `Asia Pacific (Singapore) ap-southeast-1` nếu tài khoản/quota hỗ trợ.

### Tạo S3 bucket

1. Vào AWS Console → **S3** → **Create bucket**.
2. Đặt tên duy nhất, ví dụ `employment-sagemaker-<ten-ban>-<account-id>`.
3. Chọn đúng Region đã chọn ở trên.
4. Giữ Block Public Access bật.
5. Chọn **Create bucket**.
6. Trong bucket, tạo các folder sau:

```text
raw/enrollies/
raw/education/
raw/experience/
raw/training/
raw/city/
raw/employment/
processed/
output/
```

### Upload các file

Upload file vào đúng vị trí:

```text
raw/enrollies/enrollies.csv
raw/education/enrollies_education.csv
raw/experience/work_experience.csv
raw/training/training_hours.csv
raw/city/city_dev_index.csv
raw/employment/employment.csv
```

Không để tất cả file trong cùng một folder: sáu bảng có schema khác nhau và không phải là các partition của cùng một dataset.

### Mở Canvas

1. AWS Console → **Amazon SageMaker AI** → **Studio**.
2. Nếu chưa có Domain, tạo Domain và User profile theo wizard. Chọn execution role được tạo bởi SageMaker hoặc role của tổ chức.
3. Mở Studio của User profile.
4. Trong Studio, mở **Canvas** / **Run Canvas**.

Nếu không thấy Canvas, quản trị viên cần cấp role của bạn quyền Canvas. Policy AWS managed thường dùng để bắt đầu là `AmazonSageMakerCanvasFullAccess`; role còn phải có quyền đọc/ghi bucket S3 vừa tạo. Trong môi trường production, giới hạn policy đúng bucket thay vì dùng quyền rộng.

## 3. Ghép dữ liệu trong Data Wrangler

Canvas chỉ train được từ **một bảng tabular**. Sáu bảng trên phải được ghép bằng Data Wrangler trước.

1. Trong Canvas, mở **Data Wrangler** ở thanh điều hướng trái.
2. Chọn **Create data flow**.
3. Chọn **Import data** → **Amazon S3**.
4. Import lần lượt cả sáu file CSV từ bucket.
5. Dùng `enrollies.csv` làm bảng gốc.

### Các join cần tạo

Tại node bảng gốc, chọn dấu **+** → **Join**. Thực hiện theo thứ tự sau:

| Bảng bên phải | Cột bên trái | Cột bên phải | Loại join |
|---|---|---|---|
| `enrollies_education.csv` | `enrollee_id` | `enrollee_id` | Left outer |
| `work_experience.csv` | `enrollee_id` | `enrollee_id` | Left outer |
| `training_hours.csv` | `enrollee_id` | `enrollee_id` | Left outer |
| `city_dev_index.csv` | `city` | `City` | Left outer |
| `employment.csv` | `enrollee_id` | `enrollee_id` | Inner |

Lý do dùng **Left outer**: vẫn giữ người học dù bảng feature phụ thiếu dữ liệu. Dùng **Inner** với `employment.csv`: model train chỉ cần các người có nhãn thật.

### Đổi tên và chọn cột

Trên flow sau join city, dùng **Add transform → Manage columns / Rename column**:

```text
City → city
City Development Index → city_development_index
```

Xóa cột `full_name`. Không dùng `enrollee_id` làm feature train vì đây là ID, không mang ý nghĩa dự đoán.

Bộ cột cuối cùng cần có là:

```text
city
gender
enrolled_university
education_level
major_discipline
relevent_experience
experience
company_size
company_type
last_new_job
training_hours
city_development_index
employed
```

### Làm sạch dữ liệu

Tại node cuối, chọn **Add transform**:

1. Với cột text (`gender`, `education_level`, `company_size`, …), chọn **Handle missing values** và thay giá trị thiếu bằng `unknown`.
2. Với `training_hours` và `city_development_index`, đặt data type là numeric và thay giá trị thiếu bằng **median**.
3. Kiểm tra `employed` là numeric/categorical và chỉ có hai nhãn `0`, `1`.
4. Tùy chọn: chạy **Data quality and insights report** để xem missing values và phân phối label.

## 4. Xuất bảng đã ghép lên S3

1. Ở node cuối của flow, chọn dấu **+** → **Add destination** → **Amazon S3**.
2. Chọn **CSV**.
3. Đặt output prefix:

```text
s3://YOUR_BUCKET/processed/employment/
```

4. Chọn **Configure job**.
5. Giữ cấu hình compute nhỏ cho bài demo, xác nhận execution role có quyền S3, sau đó chọn **Run**.
6. Theo dõi tới khi Processing job thành công.

Trong S3, bạn sẽ thấy một hoặc nhiều file CSV output. Đây là dataset dùng để train. Có thể đặt lại/copy một file output thành tên dễ nhớ, ví dụ `processed/employment/employment_train.csv`, ngay trong giao diện S3.

> Đừng chọn “Deploy with Data Wrangler transforms” sau này: flow này có join nhiều bảng. Join chỉ cần chạy trước khi train hoặc trước batch scoring, không thể đóng trực tiếp cùng endpoint transform.

## 5. Train model trong Canvas

1. Trong Canvas, chọn **My models** → **New model**.
2. Đặt tên model: `employment-model`.
3. Chọn loại bài toán **Predictive analysis** → **Create**.
4. Ở **Select dataset**, chọn dataset CSV đã xuất từ `processed/employment/`. Nếu chưa thấy, chọn **Import** → **Tabular** → **Amazon S3**, sau đó chọn file CSV.
5. Chọn **Select dataset**.
6. Ở tab **Build**, đặt **Target column** là `employed`.
7. Canvas phải nhận ra đây là **2-category prediction**. Nếu không, vào **Configure model** và chọn loại này.
8. Xác nhận `enrollee_id` và `full_name` không xuất hiện trong danh sách feature được chọn.

### Chọn loại build

| Lựa chọn | Dùng khi nào | Khuyến nghị |
|---|---|---|
| Quick build | Kiểm tra nhanh flow/dataset | Chạy trước một lần |
| Standard build | So sánh nhiều candidate và tuning | Dùng cho kết quả demo/báo cáo |

Với Standard build, trong **Configure model** có thể chọn:

- Training method: `Auto`.
- Objective metric: `F1` nếu hai lớp mất cân bằng và cần cân đối precision/recall; hoặc `AUC` nếu mục tiêu là xếp hạng rủi ro.
- Data split: để mặc định hoặc 80% train / 20% validation.

Chọn **Quick build** để test hoặc **Standard build** để train chính thức. Có thể rời màn hình; trạng thái sẽ thành **Ready** khi hoàn tất.

## 6. Đánh giá model

1. Vào **My models** → chọn `employment-model`.
2. Mở tab **Analyze**.
3. Xem model score, confusion matrix và feature importance.
4. Với Standard build, chọn **Model leaderboard** để so sánh các candidate.

Nên ghi lại ít nhất các chỉ số:

| Chỉ số | Ý nghĩa |
|---|---|
| AUC | Khả năng xếp người có/không có việc làm đúng theo xác suất |
| F1 | Cân bằng giữa precision và recall |
| Precision | Trong các người model dự đoán có việc, tỷ lệ đúng |
| Recall | Trong các người thực tế có việc, tỷ lệ được model nhận ra |
| Accuracy | Tỷ lệ dự đoán đúng tổng thể |

Không chỉ chọn model có accuracy cao nhất nếu nhãn `employed` bị mất cân bằng; ưu tiên F1/AUC và xem confusion matrix.

## 7. Dự đoán không cần endpoint

Để demo trong Canvas mà không phát sinh endpoint realtime:

1. Mở model đã Ready → tab **Predict**.
2. Chọn **Manual** để nhập một record, hoặc **Batch prediction** để upload CSV mới.
3. Dataset dự đoán phải có đúng feature columns như khi train, nhưng **không có `employed`**.
4. Canvas trả về nhãn dự đoán và xác suất.

Với data mới từ nhiều bảng, cần lặp lại logic join trong Data Wrangler trước khi batch prediction: join profile, education, experience, training, city index thành một bảng feature duy nhất.

## 8. Deploy SageMaker endpoint (tùy chọn)

Chỉ làm bước này khi cần ứng dụng/web service gọi dự đoán realtime.

1. Mở model → tab **Deploy**.
2. Chọn **Deploy to endpoint**.
3. Đặt tên, ví dụ `employment-predictor-demo`.
4. Chọn instance type theo quota tài khoản.
5. Đặt initial instance count là `1`.
6. Chọn **Deploy**.
7. Chờ trạng thái endpoint là `InService`.
8. Test trước trong Canvas bằng chức năng test deployment; sau đó ứng dụng bên ngoài có thể gọi endpoint bằng SageMaker Runtime API.

Input endpoint phải là một record **đã có đủ 12 feature** như dataset train. Endpoint không tự đọc sáu file nguồn hay tự join theo `enrollee_id`.

## 9. Dọn dẹp để tránh chi phí

Sau demo:

1. Canvas → model → **Deploy** → xóa deployment/endpoint `employment-predictor-demo`.
2. SageMaker AI Console → **Inference → Endpoints**: kiểm tra endpoint đã bị xóa.
3. Xóa Processing job không dùng nữa nếu cần.
4. Giữ flow/model/S3 nếu còn dùng; nếu xóa S3, cẩn thận không xóa dữ liệu raw muốn lưu.

Endpoint realtime vẫn tính phí khi trạng thái `InService`, kể cả không có request. Processing và Standard build cũng phát sinh chi phí theo thời gian chạy.

## 10. Khắc phục lỗi không có quyền deploy model

Nếu Canvas hiển thị thông báo sau khi chọn **Deploy to endpoint**:

```text
You don't have permission to deploy models. Please contact your administrator for support.
```

Đây là lỗi IAM/quyền cấu hình Canvas, không phải lỗi data hoặc model. Chỉ AWS administrator mới có thể cấp quyền này.

### Việc administrator cần làm

1. Vào AWS Console → **Amazon SageMaker AI** → **Admin configurations** → **Domains**.
2. Chọn Domain của bạn.
3. Mở tab **User profiles** và chọn User profile đang dùng Canvas.
4. Mở tab **App Configurations**.
5. Ở phần **Canvas**, chọn **Edit**.
6. Trong **ML Ops configuration**, bật **Enable direct deployment of Canvas models**.
7. Chọn **Submit** để lưu.
8. Vào AWS Console → **IAM** → **Roles** → chọn **SageMaker execution role** gắn với User profile đó.
9. Ở tab **Permissions**, chọn **Add permissions** → **Attach policies**.
10. Tìm và gắn AWS managed policy:

```text
AmazonSageMakerCanvasDirectDeployAccess
```

Policy này cấp các quyền tạo, xem, cập nhật, xóa và gọi endpoint do Canvas tạo ra. Role vẫn phải có quyền đọc model artifacts và S3 bucket đang dùng; `AmazonSageMakerCanvasFullAccess` thường đã bao gồm các quyền Canvas cơ bản cho môi trường demo.

### Việc bạn cần làm sau khi admin cấp quyền

1. Đóng/đăng xuất Canvas.
2. Mở lại SageMaker Studio → **Run Canvas**.
3. Vào **My models** → model đã Ready → tab **Deploy**.
4. Chọn **Deploy to endpoint** và thử lại.

Nếu vẫn không deploy được, gửi administrator tên Region, SageMaker Domain, User profile và ảnh lỗi mới. Admin cũng cần kiểm tra quota endpoint của SageMaker AI trong Region đó.

## 11. Lỗi thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Không thấy AutoML | Studio mới đã chuyển AutoML UI sang Canvas | Mở **Canvas → My models → New model** |
| Không thấy Canvas | Role không có quyền Canvas | Nhờ admin gắn `AmazonSageMakerCanvasFullAccess` và quyền S3 |
| Không import được `.xlsx` | Canvas tabular chỉ hỗ trợ CSV/Parquet | Lưu Excel thành CSV UTF-8 trước |
| Không thấy data S3 | Sai Region hoặc role không có quyền bucket | Dùng cùng Region và kiểm tra quyền S3 |
| Model không build được | Target sai type hoặc thiếu label | Chọn `employed`, kiểm tra chỉ có 0/1 |
| Không deploy được | Endpoint quota bằng 0/không đủ | Kiểm tra **Service Quotas → SageMaker AI** hoặc dùng instance được cấp quota |
| Không có quyền deploy model | Canvas direct deployment bị tắt hoặc role thiếu policy | Bật **Enable direct deployment of Canvas models** và gắn `AmazonSageMakerCanvasDirectDeployAccess` |
| Dự đoán endpoint lỗi schema | Thiếu/khác tên feature | Gửi đúng các feature đã train, không gửi `employed` |

## Tài liệu AWS tham khảo

- [Canvas: tạo dataset tabular](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-import-dataset.html)
- [Canvas: build model phân loại](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-build-model-how-to.html)
- [Data Wrangler: import data](https://docs.aws.amazon.com/sagemaker/latest/dg/data-wrangler-import.html)
- [Data Wrangler: export S3](https://docs.aws.amazon.com/sagemaker/latest/dg/data-wrangler-data-export.html)
- [Canvas: đánh giá model](https://docs.aws.amazon.com/sagemaker/latest/dg/canvas-scoring.html)
