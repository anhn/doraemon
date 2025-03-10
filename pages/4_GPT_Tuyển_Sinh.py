import streamlit as st
import os
from openai import OpenAI
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, util
from pymongo import MongoClient
from datetime import datetime
from streamlit_feedback import streamlit_feedback
import requests
import uuid
import time

# Load SBERT model
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB Connection
MONGO_URI = st.secrets["mongo"]["uri"]  # Load MongoDB URI from secrets
PERPLEXITY_API = st.secrets["perplexity"]["key"]
DB_NAME = "utt_detai25"
FAQ_COLLECTION = "faqtuyensinh"
CHATLOG_COLLECTION = "chatlog"

# Load OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-ada-002"
GPT_MODEL = "gpt-4-turbo"

client_mongo = MongoClient(MONGO_URI)
db = client_mongo[DB_NAME]
faq_collection = db[FAQ_COLLECTION]
chatlog_collection = db[CHATLOG_COLLECTION]

context_string = """ĐỀ ÁN TUYỂN SINH  NĂM 2024

I. Thông tin chung 
1. Tên cơ sở đào tạo: TRƯỜNG ĐH CÔNG NGHỆ GIAO THÔNG VẬN TẢI
2. Mã trường: GTA
3. Địa chỉ các trụ sở (trụ sở chính và phân hiệu)
- Trụ sở chính: Phường Đồng Tâm, Tp. Vĩnh Yên, Tỉnh Vĩnh Phúc
- Phân hiệu Hà Nội: 54 Triều Khúc, Thanh Xuân, Tp. Hà Nội
- Trung tâm đào tạo Thái Nguyên: P. Tân Thịnh, Tp. Thái Nguyên, T. Thái Nguyên
4. Địa chỉ trang thông tin điện tử của cơ sở đào tạo: 
Trang thông tin điện tử: utt.edu.vn
5. Địa chỉ các trang mạng xã hội của cơ sở đào tạo (có thông tin tuyển sinh):
Fanpage: https://www.facebook.com/utt.vn
Zalo: https://zalo.me/dhcngtvt
6. Số điện thoại liên hệ tuyển sinh:
Văn phòng tuyển sinh: 02435526713; 
7. Tình hình việc làm của sinh viên sau khi tốt nghiệp
	 Đường link công khai việc làm của sinh viên sau khi tốt nghiệp trên trang thông tin điện tử  của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html
 Kết quả khảo sát sinh viên đại học chính quy có việc làm trong khoảng thời gian 12 tháng kể từ khi được công nhận tốt nghiệp được xác định theo từng ngành, lĩnh vực đào tạo, được khảo sát ở năm liền kề trước năm tuyển sinh, đối tượng khảo sát là sinh viên đã tốt nghiệp ở năm trước cách năm tuyển sinh một năm.
STT	Lĩnh vực /Ngành đào tạo	Chỉ tiêu tuyển sinh	Số SV trúng tuyển nhập học	Số SV  tốt nghiệp	Tỷ lệ SV tốt nghiệp đã có việc làm
1	Kinh doanh và quản lý	 	 		
1.1	Quản trị kinh doanh	440	391	180	90.24
1.2	Thương mại điện tử	230	204	114	96.04
1.3	Tài chính - Ngân hàng	360	334	88	93.41
1.4	Kế toán	410	477	282	92.51
2	Máy tính và công nghệ thông tin				
2.1	Hệ thống thông tin	300	275	177	95.45
2.2	Công nghệ thông tin	630	634	121	91.38
3	Công nghệ kỹ thuật				
3.1	Công nghệ kỹ thuật công trình xây dựng	290	261	101	94.85
3.2	Công nghệ kỹ thuật giao thông	270	201	156	94.15
3.3	Công nghệ kỹ thuật cơ khí	250	290	168	91.95
3.4	Công nghệ kỹ thuật cơ điện tử	320	364	162	92.65
3.5	Công nghệ kỹ thuật ô tô	510	489	520	96.15
3.6	Công nghệ kỹ thuật điện tử – viễn thông	250	267	98	93.81
3.7	Công nghệ kỹ thuật môi trường	100	62	7	92.62
3.8	Logistics và quản lý chuỗi cung ứng	350	346	113	96.63
4	Kiến trúc và xây dựng				
4.1	Kinh tế xây dựng	340	262	57	95.38
4.2	Quản lý xây dựng	85	143	-	Ngành mới TS 2022
5	Dịch vụ vận tải				
5.1	Khai thác vận tải	425	425	72	100
	Tổng	5060	5425	2416	
8. Thông tin về tuyển sinh chính quy của 2 năm gần nhất
Đường link công khai thông tin về tuyển sinh chính quy của 2 năm gần nhất trên trang thông tin điện tử của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html
 
8.1. Phương thức tuyển sinh của 2 năm gần nhất:
Xét tuyển: sử dụng kết quả thi tốt nghiệp THPT; xét tuyển kết hợp theo đề án riêng của Trường.
8.2. Điểm trúng tuyển của 2 năm gần nhất   
TT	Lĩnh vực/ Ngành/Nhóm ngành/	Năm 2022	Năm 2023
	Tổ hợp xét tuyển: A00; A01; D01; D07	Chỉ tiêu	Số nhập học	Điểm trúng tuyển	Chỉ tiêu	Số nhập học	Điểm trúng tuyển
			Học bạ KH	THPT	Học bạ KH	THPT		Học bạ KH	THPT	Học bạ KH	THPT
1	Kinh doanh và quản lý										
1.1	Quản trị kinh doanh	440	370	90	27	23.65	440	190	201	28	22.85
1.2	Thương mại điện tử	140	97	28	28	25.35	230	59	145	29	24.07
1.3	Tài chính - Ngân hàng	210	182	40	24	23.55	360	117	217	26.5	22.55
1.4	Kế toán	410	252	166	25	23.5	410	230	247	26	22.15
2	Máy tính và công nghệ thông tin										
2.1	Mạng máy tính và truyền thông dữ liệu	180	141	38	24	24.05					
2.2	Hệ thống thông tin	220	153	59	25	24.4	300	75	200	27	21.9
2.3	Công nghệ thông tin	400	282	140	28	25.3	630	230	404	28.5	23.1
3	Công nghệ kỹ thuật										
3.1	Công nghệ kỹ thuật công trình xây dựng	90	36	43	20	16	290	24	237	20	16
3.2	Công nghệ kỹ thuật giao thông	100	63	24	20	16	270	40	161	20	16
3.3	Công nghệ kỹ thuật cơ khí	130	83	37	21	16.95	250	193	97	22	21.25
3.4	Công nghệ kỹ thuật cơ - điện tử	260	207	54	23	23.5	320	132	232	26	23.09
3.5	Công nghệ kỹ thuật ô tô	540	380	174	25	23.75	510	186	303	27	22.65
3.6	Công nghệ kỹ thuật điện tử – viễn thông	190	163	46	24	23.8	250	137	130	26	22.7
3.7	Công nghệ kỹ thuật môi trường	30	19	9	20	16	100	7	55	20	16
3.8	Logistics và quản lý chuỗi cung ứng	190	118	69	28.5	25.35	350	162	184	29	24.12
4	Kiến trúc và xây dựng										
4.1	Kinh tế xây dựng	135	107	28	23	22.75	340	172	90	23	21.4
4.2	Quản lý xây dựng	85	46	38	20	16.75	85	112	31	22	21.1
5	Dịch vụ vận tải										
5.1	Khai thác vận tải	250	200	49	22	23.3	42	335	90	25	23.6


 
9. Thông tin danh mục ngành được phép đào tạo: Đường link công khai danh mục ngành được phép đào tạo trên trang thông tin điện tử của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html
STT	Tên ngành	Mã ngành	Số văn bản cho phép mở ngành	Ngày tháng năm ban hành văn bản cho phép mở ngành	Số quyết định chuyển đổi tên ngành (gần nhất)	Ngày tháng năm ban hành Số quyết định chuyển đổi tên ngành (gần nhất)	Trường tự chủ QĐ hoặc Cơ quan có thẩm quyền cho phép	Năm bắt đầu đào tạo	Năm đã tuyển sinh và đào tạo gần nhất với năm tuyển sinh
(1)	(2)	(3)	(4)	(5)	(6)	(7)	(8)	(9)	(10)
1	Quản lý xây dựng	9580302	1385 /QĐ-BGDĐT	25/05/2022			Bộ GDĐT	2022	2022
2	Kỹ thuật xây dựng công trình đặc biệt	9580206	5031/QĐ-BGDĐT	19/11/2018			Bộ GDĐT	2021	2021
3	Kỹ thuật xây dựng công trình giao thông	9580205	5031/QĐ-BGDĐT	19/11/2018			Bộ GDĐT	2020	2021
4	Kỹ thuật cơ khí động lực	9520116	2341/QĐ- BGDĐT	12/07/2021			Bộ GDĐT	2022	2022
5	Quản lý kinh tế	9310110	45/QĐ-BGDĐT	05/01/2022			Bộ GDĐT	2022	2022
6	Tổ chức và quản lý vận tải	8840103	938/QĐ-BGDĐT	24/03/2017			Bộ GDĐT	2018	2021
7	Quản lý xây dựng	8580302	968/QĐ-BGDĐT	03/06/2018			Bộ GDĐT	2018	2021
8	Kinh tế xây dựng	8580301	3726/QĐ-BGDĐT	27/10/2021			Bộ GDĐT	2022	2022
9	Kỹ thuật xây dựng công trình giao thông	8580205	4582/QĐ-BGDĐT	20/10/2015			Bộ GDĐT	2016	2021
10	Kỹ thuật xây dựng	8580201	2392/QĐ-BGDĐT	13/07/2016	935/QĐ-BGDĐT	14/03/2018	Bộ GDĐT	2016	2021
11	Kỹ thuật cơ khí động lực	8520116	4582/QĐ-BGDĐT	20/10/2015			Bộ GDĐT	2016	2021
12	Kế toán	8340301	2392/QĐ-BGDĐT	13/07/2016			Bộ GDĐT	2016	2021
13	Quản trị kinh doanh	8340101	2392/QĐ-BGDĐT	13/07/2016			Bộ GDĐT	2016	2021
14	Quản lý kinh tế	8310110	968/QĐ-BGDĐT	03/06/2018			Bộ GDĐT	2018	2021
15	Khai thác vận tải	7840101	5162/QĐ-BGDĐT	05/11/2013			Bộ GDĐT	2014	2022
16	Quản lý xây dựng	7580302	2627/QĐ-ĐH CNGTVT	28/07/2021			Trường ĐH Công nghệ GTVT	2022	2023
17	Kinh tế xây dựng	7580301	5162/QĐ-BGDĐT	05/11/2013			Bộ GDĐT	2014	2023
18	Logistics và quản lý chuỗi cung ứng	7510605	2148/QĐ-BGDĐT	08/06/2018			Bộ GDĐT	2018	2023
19	Công nghệ kỹ thuật môi trường	7510406	5382/QĐ-BGDĐT	10/11/2015			Bộ GDĐT	2015	2023
20	Công nghệ kỹ thuật điện tử – viễn thông	7510302	1088/QĐ-BGDĐT	26/03/2013	935/QĐ-BGDĐT	14/03/2018	Bộ GDĐT	2013	2023
21	Công nghệ kỹ thuật ô tô	7510205	3089/QĐ-BGDĐT	29/07/2011			Bộ GDĐT	2011	2023
22	Công nghệ kỹ thuật cơ - điện tử	7510203	1189/QĐ-BGDĐT	08/04/2015			Bộ GDĐT	2015	2023
23	Công nghệ kỹ thuật cơ khí	7510201	721/QĐ-BGDĐT	21/02/2012			Bộ GDĐT	2012	2023
24	Công nghệ kỹ thuật giao thông	7510104	3089/QĐ-BGDĐT	29/07/2011			Bộ GDĐT	2011	2023
25	Công nghệ kỹ thuật công trình xây dựng	7510102	721/QĐ-BGDĐT	21/02/2012			Bộ GDĐT	2012	2023
26	Công nghệ thông tin	7480201	2148/QĐ-BGDĐT	08/06/2018			Bộ GDĐT	2018	2023
27	Hệ thống thông tin	7480104	1088/QĐ-BGDĐT	26/03/2013			Bộ GDĐT	2013	2023
28	Mạng máy tính và truyền thông dữ liệu	7480102	1139/QĐ-BGDĐT	08/04/2015	935/QĐ-BGDĐT	14/03/2018	Bộ GDĐT	2015	2023
29	Kế toán	7340301	1165/QĐ-BGDĐT	27/03/2012			Bộ GDĐT	2012	2023
30	Tài chính - Ngân hàng	7340201	5382/QĐ-BGDĐT	10/11/2015			Bộ GDĐT	2015	2023
31	Thương mại điện tử	7340122	2148/QĐ-BGDĐT	08/06/2018			Bộ GDĐT	2018	2023
32	Quản trị kinh doanh	7340101	1165/QĐ-BGDĐT	27/03/2012			Bộ GDĐT	2012	2023
33	Luật	7380101	4336/QĐ-ĐHCNGTVT	14/06/2024			Trường ĐH Công nghệ GTVT	2024	
34	Ngôn ngữ anh	7220201	2166/QĐ-ĐHCNGTVT	27/03/2024			Trường ĐH Công nghệ GTVT	2024	
10. Điều kiện bảo đảm chất lượng (Mẫu số 03)
Đường link công khai các điều kiện đảm bảo chất lượng trên trang thông tin điện tử của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html
11. Đường link công khai Đề án tuyển sinh trên trang thông tin điện tử của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html
12. Đường link công khai Quy chế tuyển sinh của cơ sở đào tạo trên trang thông tin điện tử của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy-n756.html
13. Đường link công khai Quy chế thi tuyển sinh (nếu cơ sở đào tạo có tổ chức thi) trên trang thông tin điện tử của CSĐT: https://utt.edu.vn/tuyensinh/tuyen-sinh/dai-hoc-chinh-quy/quy-che-tuyen-sinh-dai-hoc-cua-truong-dai-hoc-cong-nghe-giao-thong-van-tai-a14676.html
14. Đường link công khai Đề án tổ chức thi (nếu cơ sở đào tạo có tổ chức thi) trên trang thông tin điện tử của CSĐT:
II. Tuyển sinh đào tạo chính quy 
1. Tuyển sinh chính quy đại học, cao đẳng (ngành Giáo dục Mầm non) 
1.1. Đối tượng, điều kiện tuyển sinh: 
- Thí sinh được công nhận tốt nghiệp THPT hoặc tương đương.
- Có đủ sức khỏe để học tập theo quy định và không không trong thời gian xét xử/thi hành án hình sự.
1.2. Phạm vi tuyển sinh: Trong cả nước
1.3. Phương thức tuyển sinh: 
- Phương thức tuyển thẳng.
- Phương thức xét học bạ kết hợp.
- Phương thức xét tuyển dựa trên kết quả thi tốt nghiệp THPT năm 2024.
- Phương thức xét tuyển dựa trên kết quả thi đánh giá tư duy do Đại học Bách khoa Hà Nội tổ chức năm 2024.
1.4. Chỉ tiêu tuyển sinh: Chỉ tiêu theo Ngành/Nhóm ngành, theo từng phương thức xét tuyển và trình độ đào tạo.
Chỉ tiêu dự kiến theo các phương thức xét tuyển trình độ Đại học hệ chính quy:
TT	Mã ngành chuẩn	Mã ngành	Tên ngành/chuyên ngành	PT xét Học bạ KH	PT xét điểm THPT	PT xét điểm Tư duy
1	7510104	GTADCBC2	Quản lý, khai thác và bảo trì đường cao tốc	30	10	0
2	7510104	GTADCBI2	Mô hình thông tin công trình (BIM) trong dự án HTGT	30	10	0
3	7510104	GTADCCD1	CNKT XD Cầu đường bộ (học tại Vĩnh Phúc)	20	20	0
4	7510104	GTADCCD2	Công nghệ kỹ thuật XD Cầu đường bộ	110	20	10
5	7510104	GTADCCH2	Hạ tầng giao thông đô thị thông minh	20	10	0
6	7510201	GTADCCK2	Công nghệ kỹ thuật Cơ khí	180	60	10
7	7510203	GTADCCN2	Công nghệ kỹ thuật cơ điện tử	120	40	10
8	7510203	GTADCCO2	Công nghệ kỹ thuật cơ điện tử trên ô tô	110	30	10
9	7510104	GTADCCS2	Xây dựng Cầu – đường sắt	30	10	0
10	7510102	GTADCDD2	CNKT công trình XD dân dụng và công nghiệp	200	20	10
11	7510104	GTADCDS2	CNKT xây dựng Đường sắt - Metro	30	10	0
12	7510302	GTADCDT2	Công nghệ kỹ thuật điện tử - viễn thông	130	50	0
13	7220201	GTADCEN2	Ngôn ngữ Anh	50	30	0
14	7340201	GTADCHL2	Hải quan và Logistics	80	40	0
15	7480104	GTADCHT2	Hệ thống thông tin	120	120	10
16	7510102	GTADCKN2	Kiến trúc nội thất	100	40	0
17	7340301	GTADCKT1	Kế toán doanh nghiệp (học tại Vĩnh Phúc)	35	10	0
18	7340301	GTADCKT2	Kế toán doanh nghiệp	300	100	30
19	7580301	GTADCKX2	Kinh tế xây dựng	190	80	0
20	7380101	GTADCLA2	Luật	30	30	0
21	7510605	GTADCLG2	Logistics và quản lý chuỗi cung ứng	180	70	0
22	7510605	GTADCLH2	Logistics và hạ tầng giao thông	40	20	0
23	7510406	GTADCMN2	Công nghệ và quản lý môi trường	80	20	0
24	7510205	GTADCOG2	Công nghệ kỹ thuật ô tô và giao thông thông minh	30	10	0
25	7510205	GTADCOT1	Công nghệ kỹ thuật Ô tô (học tại Vĩnh Phúc)	30	10	0
26	7510205	GTADCOT2	Công nghệ kỹ thuật Ô tô	250	100	20
27	7340101	GTADCQM2	Quản trị Marketing	180	60	10
28	7340101	GTADCQT2	Quản trị doanh nghiệp	150	50	10
29	7580302	GTADCQX2	Quản lý xây dựng	60	25	0
30	7340122	GTADCTD2	Thương mại điện tử	170	70	0
31	7480201	GTADCTG2	Trí tuệ nhân tạo và giao thông thông minh	40	10	0
32	7340201	GTADCTN2	Tài chính doanh nghiệp	170	70	0
33	7510104	GTADCTQ2	Thanh tra và quản lý công trình giao thông	30	10	0
34	7480201	GTADCTT1	Công nghệ thông tin (học tại Vĩnh Phúc)	25	10	0
35	7480201	GTADCTT2	Công nghệ thông tin	300	150	15
36	7840101	GTADCVL2	Logistics và vận tải đa phương thức	130	50	0
37	7510302	GTADCVM2	Công nghệ kỹ thuật vi mạch bán dẫn	40	20	0
38	7840101	GTADCVS2	Quản lý và điều hành vận tải đường sắt	20	20	0
39	7510102	GTADCXQ2	Xây dựng và quản lý hạ tầng đô thị	60	20	0
40	7510605	GTADKLG2	Logistics - Trường Đại học Tongmyong - Hàn Quốc cấp bằng	5	5	0
41	7480201	GTADKTT2	Công nghệ thông tin – ĐH Công nghệ thông tin và quản lý Ba Lan- UITM cấp bằng	5	5	0
42	7510104	GTADNCD2	Công nghệ kỹ thuật xây dựng Cầu đường bộ (tăng cường tiếng Nhật, định hướng thực tập và làm việc tại Nhật Bản)	10	10	0
43	7510302	GTADNDT2	Công nghệ kỹ thuật Điện tử - Viễn thông (tăng cường tiếng Nhật, định hướng thực tập và làm việc tại Nhật Bản)	20	10	0
44	7510605	GTADNLG2	Logistics và quản lý chuỗi cung ứng (tăng cường tiếng Nhật, định hướng thực tập và làm việc tại Nhật Bản)	20	10	0
45	7480201	GTADNTT2	Công nghệ thông tin (tăng cường tiếng Anh)	10	10	0
Tổng	3970	1585	145

Bảng tham chiếu phương thức xét tuyển với mã xét tuyển do Bộ quy định:
Phương thức	Xét tuyển thẳng	Xét học bạ kết hợp	Xét KQ thi THPT	Xét Đánh giá tư duy
Mã phương thức xét tuyển	PT1	HBKH	THPT	TDBK
Mã phương thức do Bộ quy định	300	500	100	402
Tên phương thức XT	Xét tuyển thẳng (Theo điều 8 của Quy chế)	Xét học bạ	Xét kết quả thi tốt nghiệp THPT	Sử dụng kết quả đánh giá năng lực (do đơn vị khác tổ chức) để xét tuyển
1.5. Ngưỡng đầu vào. 
- Phương thức tuyển thẳng: Theo quy chế tuyển sinh của Bộ GD&ĐT.
- Phương thức xét học bạ kết hợp: Thí sinh có điểm tổ hợp môn xét tuyển >=18.0 (điểm THM xét 3 kỳ: học kỳ 1 lớp 11, học kỳ 2 lớp 11 và học kỳ 1 lớp 12).
- Phương thức xét tuyển dựa trên kết quả thi tốt nghiệp THPT năm 2024: Công bố sau khi có kết quả thi tốt nghiệp THPT năm 2024.
- Phương xét tuyển dựa trên kết quả thi đánh giá tư duy do Đại học Bách khoa Hà Nội tổ chức năm 2024: Thí sinh có tổng điểm thi đánh giá tư duy >= 50 điểm.
1.6. Các thông tin cần thiết khác để thí sinh dự tuyển vào các ngành của trường: mã trường, mã ngành/ nhóm ngành xét tuyển, mã phương thức xét tuyển, tổ hợp xét tuyển và quy định chênh lệch điểm xét tuyển giữa các tổ hợp; các điều kiện phụ sử dụng trong xét tuyển.
- Mã trường: GTA
- Các tổ hợp xét tuyển của phương thức xét điểm thi THPT: 
Mã tổ hợp	Các môn thi của tổ hợp xét tuyển
A00	Toán, Vật lý, Hóa học
A01	Toán, Vật lý, Tiếng Anh
D01	Toán, Ngữ văn, Tiếng Anh
D07	Toán, Hóa học, Tiếng Anh
- Điểm chênh lệch giữa các tổ hợp: Bằng 0
- Đối với các thí sinh có ĐXT bằng điểm chuẩn mà số lượng thí sinh đủ điều kiện trúng tuyển lớn hơn chỉ tiêu thì ưu tiên thí sinh có thứ tự nguyện vọng nhỏ hơn.
- Thí sinh được ĐKXT không giới hạn số nguyện vọng và phải sắp xếp nguyện vọng theo thứ tự ưu tiên từ cao xuống thấp (nguyện vọng 1 là nguyện vọng cao nhất).
- Thí sinh chỉ đủ điều kiện trúng tuyển vào 1 nguyện vọng ưu tiên cao nhất trong danh sách các nguyện vọng đã đăng ký trên hệ thống xét tuyển của Trường.
- Xét tuyển theo ngành, lấy điểm từ cao xuống thấp cho đến khi hết chỉ tiêu, không phân biệt thứ tự nguyện vọng giữa các thí sinh.
- Trong trường hợp số lượng thí sinh đủ điều kiện trúng tuyển không đạt chỉ tiêu của một phương thức, chỉ tiêu còn lại của phương thức đó chuyển sang phương thức khác.
1.7. Tổ chức tuyển sinh: Thời gian; hình thức, điều kiện nhận hồ sơ dự tuyển/thi tuyển; các điều kiện xét tuyển/thi tuyển.
- Phương thức tuyển thẳng: Thí sinh thực hiện theo quy định, kế hoạch của Bộ Giáo dục và Đào tạo.
- Phương thức xét học bạ kết hợp:
Cách tính điểm xét tuyển (ĐXT):
Điểm xét tuyển tối đa là 30.00 điểm, làm tròn đến hai chữ số thập phân. Điểm xét tuyển (ĐXT) được tính như sau:
ĐXT =M0 + M1+ M2 + M3 + Điểm ưu tiên (nếu có)
Trong đó:
+ M0: Tổng điểm quy đổi (theo Bảng quy đổi điểm thang điểm 10 của tất cả các điều kiện ưu tiên).
+ M1, M2, M3: Điểm trung bình của 3 kỳ (học kỳ 1 lớp 11, học kỳ 2 lớp 11 và học kỳ 1 lớp 12) của các môn trong tổ hợp xét tuyển.
+ Điểm chênh lệch giữa các tổ hợp: bằng 0
+ Điểm ưu tiên: Bao gồm điểm ưu tiên khu vực và điểm ưu tiên đối tượng theo Quy chế tuyển sinh của Bộ GD&ĐT.
- Đối với các thí sinh có ĐXT bằng điểm trúng tuyển mà số lượng thí sinh đủ điều kiện trúng tuyển lớn hơn chỉ tiêu thì ưu tiên theo thứ tự nguyện vọng và điểm môn Toán. Đối với thí sinh đạt tổng điểm từ 22,5 trở lên, công thức tính mức điểm ưu tiên khu vực thí sinh được hưởng = [(30 - tổng điểm đạt được của thí sinh)/7,5] x mức điểm ưu tiên được xác định thông thường, làm tròn đến 2 chữ số phần thập phân.
+ Hình thức đăng ký tuyển sinh: Đăng ký trực tuyến trên hệ thống xét tuyển của Trường Đại học Công nghệ Giao thông vận tải, đồng thời đăng ký xác nhận nguyện vọng trên Cổng thông tin tuyển sinh của Bộ GD&ĐT theo quy định.
+ Thời gian đăng ký dự kiến:
Đợt 1: Từ ngày 15/3/2024 đến ngày 27/4/2024.
Đợt 2: Từ ngày 03/5/2024 đến ngày 15/6/2024
- Phương thức xét tuyển dựa trên kết quả thi tốt nghiệp THPT năm 2024: Thí sinh thực hiện theo quy định, kế hoạch của Bộ Giáo dục và Đào tạo.
Cách tính điểm xét tuyển (ĐXT):
+ Điểm xét tuyển theo thang điểm 30 làm tròn đến hai chữ số thập phân. Điểm xét tuyển được tính như sau:
ĐXT = M1 + M2 + M3 + Điểm ưu tiên (nếu có)
Trong đó:  
+ M1, M2, M3 là kết quả điểm thi tốt nghiệp THPT năm 2024 của các môn thi thuộc tổ hợp môn xét tuyển;
+ Điểm ưu tiên: Bao gồm điểm ưu tiên khu vực và điểm ưu tiên đối tượng theo Quy chế tuyển sinh của Bộ GD&ĐT. Đối với thí sinh đạt tổng điểm từ 22,5 trở lên, công thức tính mức điểm ưu tiên khu vực thí sinh được hưởng = [(30 - tổng điểm đạt được của thí sinh)/7,5] x mức điểm ưu tiên được xác định thông thường, làm tròn đến 2 chữ số phần thập phân;
Lưu ý: Đối với thí sinh không có điểm thi tốt nghiệp môn Tiếng Anh mà có chứng chỉ IELTS để xét miễn thi tốt nghiệp năm 2024 thì điểm môn Tiếng Anh được tính là 10.0 trong các tổ hợp môn xét tuyển có môn Tiếng Anh (A01, D01, D07), các thí sinh có điểm thi tốt nghiệp môn Tiếng Anh thì sẽ lấy điểm thi để xét.
- Phương xét tuyển dựa trên kết quả thi đánh giá tư duy do Đại học Bách khoa Hà Nội tổ chức năm 2024:
+ Hình thức đăng ký tuyển sinh: Đăng ký trực tuyến trên hệ thống Cổng thông tin tuyển sinh của Bộ GD&ĐT theo quy định.
+ Thời gian đăng ký: thực hiện theo quy định, kế hoạch của Bộ Giáo dục và Đào tạo.
Cách tính điểm xét tuyển (ĐXT):
- Điểm xét tuyển theo thang điểm 30 làm tròn đến hai chữ số thập phân. Điểm xét tuyển được tính như sau:
ĐXT = Tổng điểm thi ×30/100 + Điểm ưu tiên (nếu có)
Trong đó: Điểm ưu tiên gồm điểm ưu tiên khu vực và điểm ưu tiên đối tượng theo Quy chế tuyển sinh của Bộ GD&ĐT.
- Đối với các thí sinh có ĐXT bằng điểm trúng tuyển mà số lượng thí sinh đủ điều kiện trúng tuyển lớn hơn chỉ tiêu thì ưu tiên theo tiêu chí phụ là thứ tự nguyện vọng.
- Điểm xét tuyển của thí sinh tối đa là 30.0 điểm, thí sinh chỉ  được công nhận 1 nguyện vọng trúng tuyển có đủ điều kiện trúng tuyển về điểm và có thứ tự nguyện vọng nhỏ nhất trong số các nguyện vọng đăng ký.
+ Điểm ưu tiên: Bao gồm điểm ưu tiên khu vực và điểm ưu tiên đối tượng theo Quy chế tuyển sinh của Bộ GD&ĐT. Đối với thí sinh đạt tổng điểm từ 22,5 trở lên, công thức tính mức điểm ưu tiên khu vực thí sinh được hưởng = [(30 - tổng điểm đạt được của thí sinh)/7,5] x mức điểm ưu tiên được xác định thông thường, làm tròn đến 2 chữ số phần thập phân.
1.8. Chính sách ưu tiên: Xét tuyển thẳng; ưu tiên xét tuyển.
Đối với phương thức xét học bạ kết hợp:
- Thí sinh được cộng điểm ưu tiên xét tuyển nếu có một trong các điều kiện sau:
+ Thí sinh đoạt giải Nhất, Nhì, Ba trong kỳ thi học sinh giỏi THPT cấp tỉnh/thành phố các môn Toán, Vật lý, Hóa học, Tin học, Tiếng Anh, Ngữ văn.
+ Thí sinh có một trong các Chứng chỉ tiếng Anh quốc tế IELTS ≥ 4.5 (chứng chỉ trong thời hạn 24 tháng tính đến ngày đăng ký xét tuyển).
+ + Thí sinh đạt từ 01 kỳ học sinh giỏi trở lên (trong các kỳ học lớp 10, 11 và kỳ 1 lớp 12).
+ Bảng quy đổi điểm sang thang điểm 10:
Chứng chỉ Tiếng Anh	Đoạt giải  HSG cấp tỉnh/TP	Đạt HSG THPT
Tiếng Anh IELTS	Điểm quy đổi	Giải	Điểm quy đổi	Số kỳ HSG	Điểm quy đổi
4.5-5.0	1.0	Ba	1.0	1 kỳ	0.3
5.5	1.5	Nhì	2.0	2 kỳ	0.6
6.0	2.0	Nhất	3.0	3 kỳ	0.9
6.5	2.5			4 kỳ	1.2
7.0-9.0	3.0			5 kỳ	1.5
1.9. Lệ phí xét tuyển/thi tuyển.
- Phương thức tuyển thẳng: Lệ phí đăng ký xét tuyển và xử lý nguyện vọng trên Cổng thông tin của Bộ GD&ĐT hoặc dịch vụ công quốc gia thực hiện theo hướng dẫn của Bộ GD&ĐT. 
- Phương thức xét học bạ kết hợp:
+ Lệ phí thu, kiểm tra hồ sơ đăng ký xét tuyển đại học chính quy tại Trường Đại học Công nghệ Giao thông vận tải: 50.000 đồng/thí sinh. 
+ Lệ phí đăng ký xét tuyển và xử lý nguyện vọng trên Cổng thông tin của Bộ GD&ĐT hoặc dịch vụ công quốc gia thực hiện theo hướng dẫn của Bộ GD&ĐT.
- Phương thức xét tuyển dựa trên kết quả thi tốt nghiệp THPT năm 2024 và phương thức xét tuyển dựa trên kết quả thi đánh giá tư duy do Đại học Bách khoa Hà Nội tổ chức năm 2024: Lệ phí đăng ký xét tuyển và xử lý nguyện vọng trên Cổng thông tin của Bộ GD&ĐT hoặc dịch vụ công quốc gia thực hiện theo hướng dẫn của Bộ GD&ĐT.
1.10. Học phí dự kiến với sinh viên chính quy; lộ trình tăng học phí tối đa cho từng năm (nếu có): 
Mức học phí năm học 2024-2025 dự kiến là 470000đ/1 tín chỉ cho tất cả các chương trình đào tạo đại trà; với các chương trình tăng cường ngoại ngữ học phí bằng 1.5 lần học phí chương trình đại trà; với các chương trình liên kết quốc tế, học phí theo đề án được phê duyệt.
1.11. Thời gian dự kiến tuyển sinh các đợt trong năm.
	- Đợt 1: Theo kế hoạch của Bộ Giáo dục và Đào tạo.
	- Đợt bổ sung (nếu có): Sau ngày 22/8/2024
1.12. Các phương án xử lý rủi ro khi triển khai công tác tuyển sinh và cam kết trách nhiệm.
- Đối với các phương thức: Xét học bạ kết hợp thí sinh thực hiện đăng ký nguyện vọng xét tuyển, theo thông báo tuyển sinh của Trường Đại học Công nghệ GTVT đồng thời đăng ký xác nhận nguyện vọng trên hệ thống của Bộ GD&ĐT.
- Trường hợp thí sinh đăng ký nguyện vọng xét tuyển trên hệ thống của Trường, không đăng ký nguyện vọng trên hệ thống của Bộ GD&ĐT được coi như hồ sơ không hợp lệ và Nhà trường sẽ bị hủy bỏ kết quả công nhận đủ điều kiện trúng tuyển của thí sinh trên hệ thống xét tuyển của Trường Đại học Công nghệ GTVT theo quy chế tuyển sinh năm 2024.
- Trường hợp thí sinh đăng ký nguyện vọng xét tuyển trên hệ thống của Bộ GD&ĐT, không đăng ký nguyện vọng xét tuyển trên hệ thống của Trường Đại học Công nghệ GTVT được coi như hồ sơ không hợp lệ và Nhà trường sẽ không công nhận kết quả đăng ký nguyện vọng trên hệ thống của Bộ GD&ĐT.
- Nếu thí sinh khai báo không chính xác thông tin, số liệu trên hệ thống đăng ký xét tuyển của Trường Đại học Công nghệ GTVT, được xử lý như sau:
+ Trường hợp thông tin sai lệch có ảnh hưởng đến kết quả tuyển sinh (đủ/không đủ điều kiện trúng tuyển) được coi như thí sinh đã vi phạm quy chế tuyển sinh và bị hủy kết quả xét tuyển.
+ Trường hợp thông tin sai lệch không ảnh hưởng đến điều kiện trúng tuyển (thông tin ngày tháng năm sinh, quê quán,..), thí sinh được làm đơn đề nghị cập nhật thông tin, Hội đồng tuyển sinh Nhà trường xem xét để công nhận kết quả xét tuyển.
- Thí sinh trúng tuyển đã xác nhận nhập học nhưng nhập học muộn quá thời gian quy định theo thông báo của Trường Đại học Công nghệ GTVT, được xử lý như sau:
+ Trường hợp có lý do chính đáng được Nhà trường chấp nhận cho nhập học bổ sung nếu có đơn xin nhập học muộn và có minh chứng cho lý do chính đáng.
	+ Trường hợp không có lý do chính đáng coi như thí sinh từ chối việc nhập học và không được chấp nhận nhập học bổ sung.
1.13. Thông tin tuyển sinh các ngành đào tạo đặc thù có nhu cầu cao về nhân lực trình độ đại học đáp ứng yêu cầu phát triển kinh tế - xã hội của đất nước. 
1.13.1. Thông tin về doanh nghiệp hợp tác đào tạo. 
1.13.2. Các thông tin triển khai áp dụng cơ chế đào tạo đặc thù có nhu cầu cao về nhân lực trình độ đại học (không trái các quy định hiện hành).
1.14. Tài chính:
1.14.1. Tổng nguồn thu hợp pháp/năm của trường: 320.000 triệu đồng.
	1.14.2. Tổng chi phí đào tạo trung bình 1 sinh viên/năm của năm liền trước năm tuyển sinh: 20 triệu đồng.
1.15. Các nội dung khác (không trái quy định hiện hành).
2. Tuyển sinh đào tạo đại học, cao đẳng chính quy với đối tượng tốt nghiệp từ trung cấp trở lên
2.1. Tuyển sinh trình độ đại học liên thông từ cao đẳng cho hình thức đào tạo chính quy 
2.1.1. Đối tượng, điều kiện tuyển sinh: Thí sinh đã tốt nghiệp cao đẳng của Trường ĐH CNGTVT hoặc các trường Đại học, Cao đẳng khác có cùng ngành đào tạo.
2.1.2. Phạm vi tuyển sinh: Tuyển sinh trong cả nước.
2.1.3. Phương thức tuyển sinh (thi tuyển, xét tuyển hoặc kết hợp thi tuyển và xét tuyển): Xét tuyển. 
2.1.4. Chỉ tiêu tuyển sinh: Chỉ tiêu theo ngành,  theo từng phương thức xét tuyển và trình độ đào tạo: 

TT	Trình độ đào tạo	Mã ngành xét tuyển	
Tên ngành
xét tuyển	Mã phương thức xét tuyển	Tên phương thức xét tuyển	Chỉ tiêu (dự kiến)	Số văn bản quy định	Ngày tháng năm ban hành văn bản	Cơ quan có  thẩm quyền cho phép hoặc trường tự chủ ban hành	Năm bắt đầu đào tạo
(1)	(2)	(3)	(4)	(5)	(6)	(7)	(8)	(9)	(10)	(11)
1.	ĐH Liên thông	7510104	Công nghệ kỹ thuật giao thông	500	Sử dụng phương thức khác	60	2872/QĐ-BGDĐT	15/05/2012	Bộ Giáo dục và Đào tạo	2012
2.	ĐH Liên thông	7510102	Công nghệ kỹ thuật công trình xây dựng	500	Sử dụng phương thức khác	60	6368/QĐ-BGDĐT	26/09/2012	Bộ Giáo dục và Đào tạo	2013
3	ĐH Liên thông	7510205	Công nghệ kỹ thuật ô tô	500	Sử dụng phương thức khác	60	2872/QĐ-BGDĐT	15/05/2012	Bộ Giáo dục và Đào tạo	2012
4	ĐH Liên thông	7340301	Kế toán	500	Sử dụng phương thức khác	30	6368/QĐ-BGDĐT	26/09/2012	Bộ Giáo dục và Đào tạo	2013
 
tổng điểm môn cơ sở ngành và chuyên ngành, tổng điểm ≥ 11.0 (theo thang điểm 20)
2.1.6. Các thông tin cần thiết khác để thí sinh dự tuyển vào các ngành của trường: Xét tuyển điểm lấy từ cao xuống thấp đến khi đủ chỉ tiêu. Điểm xét tuyển lấy đến 2 chữ số thập phân. Nếu nhiều hồ sơ có điểm xét tuyển bằng nhau thì lấy điểm môn cơ sở ngành.
2.1.7. Tổ chức tuyển sinh: Thời gian; điều kiện nhận hồ sơ dự tuyển, hình thức nhận hồ sơ dự tuyển /thi tuyển; các điều kiện xét tuyển/thi tuyển, tổ hợp môn thi/bài thi đối với từng ngành đào tạo: Thời gian; hình thức nhận hồ sơ ĐKXT/thi tuyển; các điều kiện xét tuyển/thi tuyển, tổ hợp môn thi/bài thi đối với từng ngành đào tạo...
Tuyển sinh 4 đợt trong năm bắt đầu từ tháng 2/2024, hồ sơ xét tuyển nộp tại Khoa Đào tạo tại chức, Môn xét tuyển: Cơ sở ngành và chuyên ngành.
2.1.8. Chính sách ưu tiên: Xét tuyển thẳng; ưu tiên xét tuyển.
2.1.9. Lệ phí xét tuyển/thi tuyển: Theo quy định
2.1.10. Học phí dự kiến với sinh viên; Mức học phí năm học 2024-2025 thực hiện theo Nghị định 81/2021/NĐ-CP ngày 27/8/2021 của Chính phủ;
2.1.11. Thời gian dự kiến tuyển sinh các đợt trong năm: Tháng 2, 5, 8, 12/2024
2.1.12. Các nội dung khác (không trái quy định hiện hành): Địa chỉ website đăng tải thông báo tuyển sinh của trường: http://utt.edu.vn/
2.2. Tuyển sinh trình độ đại học liên thông để nhận thêm một bằng tốt nghiệp đại học của một ngành đào tạo khác cho hình thức đào tạo chính quy (Văn bằng hai)
2.2.1. Đối tượng, điều kiện tuyển sinh: Thí sinh đã tốt nghiệp và có bằng đại học 
2.2.2. Phạm vi tuyển sinh: Tuyển sinh trong cả nước.
2.2.3. Phương thức tuyển sinh (thi tuyển, xét tuyển hoặc kết hợp thi tuyển và xét tuyển): Xét tuyển.
2.2.4. Chỉ tiêu tuyển sinh: Chỉ tiêu theo ngành,  theo từng phương thức xét tuyển và trình độ đào tạo: 
TT
Trình độ đào tạo	Mã ngành xét tuyển	Tên ngành
xét tuyển	Mã phương thức xét tuyển	Tên phương thức xét tuyển	Chỉ tiêu (dự kiến)	Số văn bản quy định	Ngày tháng năm ban hành văn bản	Cơ quan có  thẩm quyền cho phép hoặc trường tự chủ ban hành	Năm bắt đầu đào tạo
(1)	(2)	(3)	(4)	(5)	(6)	(7)	(8)	(9)	(10)	(11)
1.	ĐH Văn bằng 2	Công nghệ kỹ thuật giao thông	7510104	500	Phương thức khác	40	4972/BGDĐT-GDĐH	05/10/2016	Bộ Giáo dục và Đào tạo	2016
2.	ĐH Văn bằng 2	Công nghệ kỹ thuật CTXD	7510102	500	Phương thức khác	40	385/BGDĐT-GDĐH	30/01/2018	Bộ Giáo dục và Đào tạo	2018
3	ĐH Văn bằng 2	Công nghệ kỹ thuật ô tô	7510205	500	Phương thức khác	20	4972/BGDĐT-GDĐH	05/10/2016	Bộ Giáo dục và Đào tạo	2016
4	ĐH Văn bằng 2	Kế toán	7340301	500	Phương thức khác	20	4972/BGDĐT-GDĐH	05/10/2016	Bộ Giáo dục và Đào tạo	2016
5	ĐH Văn bằng 2	Kinh tế xây dựng	7580301	500	Phương thức khác	30	385/BGDĐT-GDĐH	30/01/2018	Bộ Giáo dục và Đào tạo	2018
 
2.2.5. Ngưỡng đầu vào: Đã có bằng tốt nghiệp đại học
2.2.6. Các thông tin cần thiết khác để thí sinh dự tuyển vào các ngành của trường: Xét tuyển điểm lấy từ cao xuống thấp đến khi đủ chỉ tiêu (căn cứ vào điểm TBC tốt nghiệp).
2.2.7. Tổ chức tuyển sinh: Thời gian; điều kiện nhận hồ sơ dự tuyển, hình thức nhận hồ sơ dự tuyển /thi tuyển; các điều kiện xét tuyển/thi tuyển, tổ hợp môn thi/bài thi đối với từng ngành đào tạo:
Thời gian; hình thức nhận hồ sơ ĐKXT/thi tuyển; các điều kiện xét tuyển/thi tuyển, tổ hợp môn thi/bài thi đối với từng ngành đào tạo...
Tuyển sinh 4 đợt trong năm bắt đầu từ tháng 2/2024, hồ sơ xét tuyển nộp tại Khoa Đào tạo tại chức.
2.2.8. Chính sách ưu tiên: 
2.2.9. Lệ phí xét tuyển/thi tuyển: Theo quy định
2.2.10. Học phí dự kiến với sinh viên: Mức học phí năm học 2024-2025 thực hiện theo Nghị định 81/2021/NĐ-CP ngày 27/8/2021 của Chính phủ;
2.2.11. Thời gian dự kiến tuyển sinh các đợt trong năm: Tháng 2, 5, 8, 12/2024
2.2.12. Các nội dung khác (không trái quy định hiện hành): Địa chỉ website đăng tải thông báo tuyển sinh của trường: http://utt.edu.vn/
Cán bộ kê khai
Nguyễn Đức Sơn
ĐT: 094959628, Email: sonnguyen.utt@gmail.com	Hà Nội, ngày 12 tháng 10 năm 2024
CHỦ TỊCH HĐTS
PHÓ HIỆU TRƯỞNG
TS. Nguyễn Văn Lâm
"""
def get_ip():
    try:
        return requests.get("https://api64.ipify.org?format=json").json()["ip"]
    except:
        return "Unknown"

user_ip = get_ip()
       
# Initialize chat history in session state
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

# Set OpenAI API Key in the environment
os.environ["OPENAI_API_KEY"] = st.secrets["api"]["key"]

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_gpt4_response(question, context):
    prompt = (
        f"Một sinh viên hỏi: {question}\n\n"
        f"Dựa trên thông tin sau đây, hãy cung cấp một câu trả lời hữu ích, ngắn gọn và thân thiện. "
        f"Dẫn nguồn từ nội dung có sẵn nếu cần.\n\n"
        f"Thông tin: {context}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý tuyển sinh đại học hữu ích, chỉ dựa trên nội dung đã cung cấp."},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        return response  # Assuming response handling is done elsewhere
    except Exception as e:
        return f"Lỗi khi tạo phản hồi: {str(e)}"

# Function to save chat logs to MongoDB
def save_chat_log(user_ip, user_message, bot_response, feedback):
    """Stores chat log into MongoDB, grouped by user IP"""
    if feedback and feedback.strip():
        chat_entry = {
                "user_ip": user_ip,
                "timestamp": datetime.utcnow(),
                "user_message": user_message,
                "bot_response": bot_response,
                "is_good": False,
                "problem_detail": feedback
            }    
    else:    
        chat_entry = {
            "user_ip": user_ip,
            "timestamp": datetime.utcnow(),
            "user_message": user_message,
            "bot_response": bot_response,
            "is_good": True,
            "problem_detail" : ""
        }
    chatlog_collection.insert_one(chat_entry)
    
def stream_text(text):
    """Converts a string into a generator to work with `st.write_stream()`."""
    for word in text.split():
        yield word + " "  # Stream words with a space for a natural effect
        
# Banner Image (Replace with your actual image URL or file path)
BANNER_URL = "https://utt.edu.vn/uploads/images/site/1722045380banner-utt.png"  # Example banner image

st.markdown(
    f"""
    <style>
        .center {{
            text-align: center;
        }}
        .banner {{
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 450px; /* Adjust size as needed */
        }}
        .title {{
            font-size: 28px;
            font-weight: bold;
            color: #1E88E5; /* Education-themed blue */
            margin-top: 15px;
        }}
        .subtitle {{
            font-size: 18px;
            color: #333;
            margin-top: 5px;
        }}
    </style>

    <div class="center">
        <img class="banner" src="{BANNER_URL}">
        <p class="title">🎓 Hỗ trợ tư vấn tuyển sinh - UTT</p>
        <p class="subtitle">Hỏi tôi bất kỳ điều gì về tuyển sinh đại học!</p>
    </div>
    """,
    unsafe_allow_html=True
)
# **Chat Interface**
st.subheader("💬 Chatbot Tuyển Sinh")

# **Display Chat History**
for chat in st.session_state["chat_log"]:
    with st.chat_message("user"):
        st.write(chat["user"])
    with st.chat_message("assistant"):
        st.write(chat["bot"])
        
user_input = st.chat_input("Nhập câu hỏi của bạn...")

if user_input:
    # Show user message
    with st.chat_message("user"):
        st.write(user_input)

    response_stream = generate_gpt4_response(user_input,context_string)  # Now a generator

    with st.chat_message("assistant"):
        bot_response_container = st.empty()  # Create an empty container
        bot_response = ""  # Collect the full response
        for chunk in response_stream:
            bot_response += chunk  # Append streamed content
            bot_response_container.write(bot_response)  # Update UI in real-time

    # Save to session history
    st.session_state["chat_log"].append(
        {"user": user_input, "bot": bot_response, "is_gpt": True}
    )
    feedback=""
    # Save chat log to MongoDB
    save_chat_log(user_ip, user_input, bot_response, feedback)
    feedback = streamlit_feedback(
        feedback_type="thumbs",
        optional_text_label="[Tùy chọn] Vui lòng giải thích",
    )
    print(feedback)
    if feedback: 
        # Retrieve the latest chat log entry for the current user
        last_chat = chatlog_collection.find_one(
            {"user_ip": user_ip},
            sort=[("timestamp", -1)]  # Get the latest entry by sorting timestamp descending
        )
        if last_chat:
            # Update the existing log with feedback details, user input, and bot response
            chatlog_collection.update_one(
                {"_id": last_chat["_id"]},  # Find the correct entry
                {
                    "$set": {
                        "is_good": False if feedback else True,
                        "problem_detail": feedback,
                        "user_message": user_input,  # Update user question
                        "bot_response": bot_response  # Update bot response
                    }
                }
            )
            st.success("✅ Cảm ơn bạn đã đánh giá! Nhật ký chat đã được cập nhật.")
        else:
            st.warning("⚠️ Không tìm thấy nhật ký chat để cập nhật phản hồi.")
