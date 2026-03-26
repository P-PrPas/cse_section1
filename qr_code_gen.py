import qrcode

# URL ของไฟล์ PDF (อาจเป็น Google Drive, S3, หรือ server ของคุณ)
pdf_url = "https://drive.google.com/file/d/1Ejar-DuLjJzgJZ4jUh0UIRPfdU0ci_m6/view?usp=sharing"

# สร้าง QR Code
qr = qrcode.make(pdf_url)

# บันทึกเป็นไฟล์ภาพ
qr.save("pdf_qr.png")