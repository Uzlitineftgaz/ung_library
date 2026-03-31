# 📚 BookLore: Docker Boshqaruv Qo'llanmasi

Ushbu loyiha **Spring Boot (Java 25)**, **Angular (Node 24)** va **MariaDB** texnologiyalariga asoslangan. Loyihani ikki xil rejimda (Development va Production) boshqarish mumkin.

---

## 🛠 1. Development Mode (Ishlab chiqish rejimi)

Dasturlash jarayonida kod o'zgarishlarini darhol ko'rish uchun mo'ljallangan. Backend va Frontend alohida konteynerlarda ishlaydi.

### 🚀 Ishga tushirish
```powershell
# Konteynerlarni orqa fonda ishga tushirish
docker compose -f dev.docker-compose.yml up -d

# Agar yangi kutubxonalar qo'shilgan bo'lsa (npm/gradle), qayta build qilish
docker compose -f dev.docker-compose.yml up -d --build
```
## 🔄 Qayta ishga tushirish (Restart)

```powershell
# Faqat Backend (Spring Boot)ni restart qilish
docker compose -f dev.docker-compose.yml restart backend

# Faqat Frontend (UI)ni restart qilish
docker compose -f dev.docker-compose.yml restart ui

# Barcha servislarni o'chirib-yoqish
docker compose -f dev.docker-compose.yml restart
```

## 🔗 Bog'lanish nuqtalari:

Frontend (Angular): http://localhost:4200

Backend API: http://localhost:6060

Ma'lumotlar bazasi (MariaDB): http://localhost:3366

Remote Debug: http://localhost:5005

## 🏗 2. Production Mode (Tayyor mahsulot rejimi)

Bu rejimda Angular loyihasi build qilinib, Spring Boot ichiga (static resources) joylanadi. Natijada bitta yaxlit Docker image hosil bo'ladi.

📦 Obrazni yig'ish (Build)
Kodni o'zgartirgandan so'ng, yangi image yaratish shart:

```powershell
# Loyihani bitta obrazga yig'ish (Dockerfile asosida)
docker build -t unglibrary:latest .
```
## 🚀 Ishga tushirish
```powershell
# Asosiy docker-compose orqali ishga tushirish
docker compose up -d
```
## 🔄 Qayta ishga tushirish
```powershell
docker compose restart unglibrary
```
## 🔗 Bog'lanish nuqtasi:

Asosiy ilova: http://SERVER_IP:9999
(Eslatma: Tashqi 9999 porti ichki 6060 portiga yo'naltirilgan)

🧹 3. Texnik xizmat va Monitoring

📊 Loglarni kuzatish (Jonli)

```powershell
# Production rejimi uchun
docker logs -f unglibrary

# Development rejimi uchun
docker logs -f backend
```

## 🗑 Tozalash va Yangilash

```powershell
# Eski/ortiqcha (orphan) konteynerlarni tozalash
docker compose up -d --remove-orphans

# Bazaviy obrazlarni yangilab olish (MariaDB va h.k.)
docker compose -f dev.docker-compose.yml pull
```
## 📊 Portlar va Konfiguratsiya Jadvali

| Servis | Ichki Port (Container) | Tashqi Port (Dev Mode) | Tashqi Port (Prod Mode) |
| :--- | :---: | :---: | :---: |
| **Backend (API)** | `6060` | `6060` | **`9999`** |
| **Frontend (UI)** | `4200` | `4200` | *Backend ichiga o'ralgan* |
| **MariaDB (DB)** | `3306` | `3366` | *Faqat ichki tarmoqda* |
| **Debug Port** | `5005` | `5005` | *Yopiq* |

---

**💡 Eslatma:** * **Dev Mode**'da Frontend va Backend alohida ishlaydi.
* **Prod Mode**'da esa barcha so'rovlar yagona **9999** porti orqali amalga oshiriladi.