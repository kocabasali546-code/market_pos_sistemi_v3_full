import os
import csv
import sqlite3
import openpyxl
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# 1. FLASK UYGULAMASI
app = Flask(__name__)

# 2. İŞLETME ADI AYARI
ISLETME_ADI = "ÖZKAN MARKET & TEKEL"

@app.context_processor
def inject_isletme_adi():
    return dict(isletme_adi=ISLETME_ADI)

app.secret_key = "market_secret_key_789"
DB_NAME = "market.db"


# 3. VERİTABANI BAĞLANTISI
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# 4. VERİTABANI İLK KURULUMU
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Urunler Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT UNIQUE NOT NULL,
            urun_adi TEXT NOT NULL,
            birim_fiyat REAL NOT NULL,
            stok_miktari INTEGER NOT NULL,
            kritik_stok INTEGER DEFAULT 5,
            kategori TEXT DEFAULT 'Genel'
        )
    """)

    # Barkod Hızlı Arama İndeksi
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_barkod ON urunler(barkod)")

    # 2. Satislar & Satis Detay Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS satislar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
            toplam_tutar REAL NOT NULL,
            odeme_tipi TEXT NOT NULL,
            musteri_id INTEGER DEFAULT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS satis_detay (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            satis_id INTEGER NOT NULL,
            barkod TEXT NOT NULL,
            urun_adi TEXT NOT NULL,
            birim_fiyat REAL NOT NULL,
            adet INTEGER NOT NULL,
            toplam REAL NOT NULL
        )
    """)

    # 3. Musteriler (Veresiye Defteri)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musteriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT,
            bakiye_borc REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS veresiye_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_id INTEGER NOT NULL,
            islem_tipi TEXT NOT NULL,
            tutar REAL NOT NULL,
            tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
            aciklama TEXT
        )
    """)

    # 4. Toptancilar & Toptanci Islemleri
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS toptancilar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_adi TEXT NOT NULL,
            yetkili TEXT,
            telefon TEXT,
            borc_bakiye REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS toptanci_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            toptanci_id INTEGER NOT NULL,
            islem_tipi TEXT NOT NULL,
            tutar REAL NOT NULL,
            odeme_sekli TEXT DEFAULT 'Nakit',
            tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
            aciklama TEXT
        )
    """)

    # 5. Hizli Tuslar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hizli_tuslar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT NOT NULL UNIQUE,
            sira INTEGER DEFAULT 0
        )
    """)

    # 6. Hazir Ürün Kataloğu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hazir_katalog (
            barkod TEXT PRIMARY KEY,
            urun_adi TEXT NOT NULL,
            kategori TEXT DEFAULT 'Genel'
        )
    """)

    # --- ÖRNEK İLK VERİLER ---
    cursor.execute("SELECT COUNT(*) FROM urunler")
    if cursor.fetchone()[0] == 0:
        ornek_urunler = [
            ("8690123456789", "Ekmek 250g", 10.00, 150, 20, "Unlu Mamüller"),
            ("8690533000017", "Sırma Maden Suyu 200ml", 8.00, 200, 30, "İçecek"),
            ("8690637010011", "Sütaş Süt 1L", 35.00, 8, 10, "Süt Ürünleri"),
            ("8690504018003", "Ülker Çikolatalı Gofret 36g", 15.00, 4, 15, "Atıştırmalık"),
            ("8690526010016", "Eti Karam %70 Bitter 60g", 28.50, 85, 10, "Atıştırmalık")
        ]
        cursor.executemany("""
            INSERT INTO urunler (barkod, urun_adi, birim_fiyat, stok_miktari, kritik_stok, kategori)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ornek_urunler)

        cursor.execute("INSERT OR IGNORE INTO hizli_tuslar (barkod, sira) VALUES ('8690123456789', 1)")
        cursor.execute("INSERT OR IGNORE INTO hizli_tuslar (barkod, sira) VALUES ('8690533000017', 2)")
        cursor.execute("INSERT OR IGNORE INTO hizli_tuslar (barkod, sira) VALUES ('8690637010011', 3)")
        cursor.execute("INSERT OR IGNORE INTO hizli_tuslar (barkod, sira) VALUES ('8690504018003', 4)")

        cursor.execute("INSERT INTO musteriler (ad_soyad, telefon, bakiye_borc) VALUES ('Ahmet Yılmaz (Örnek)', '05551112233', 350.0)")
        cursor.execute("INSERT INTO toptancilar (firma_adi, yetkili, telefon, borc_bakiye) VALUES ('Bizim Toptan A.Ş.', 'Mehmet Bey', '02124440000', 1250.0)")

    cursor.execute("SELECT COUNT(*) FROM hazir_katalog")
    if cursor.fetchone()[0] == 0:
        hazir_urunler = [
            ("8690504018003", "Ülker Çikolatalı Gofret 36g", "Atıştırmalık"),
            ("8690526010016", "Eti Karam %70 Bitter 60g", "Atıştırmalık"),
            ("8690123456789", "Ekmek 250g", "Unlu Mamüller"),
            ("8690533000017", "Sırma Maden Suyu 200ml", "İçecek"),
            ("8690637010011", "Sütaş Süt 1L", "Süt Ürünleri"),
            ("8690150000018", "Coca-Cola 1.5L Original", "İçecek"),
            ("8690150000025", "Fanta Portakal 1.5L", "İçecek"),
            ("8690504001128", "Ülker Biskrem Poşet 150g", "Atıştırmalık"),
            ("8690620001156", "Çaykur Rize Turist Çayı 1000g", "Gıda"),
            ("8690504050010", "Ülker Halley Poşet 10'lu", "Atıştırmalık")
        ]
        cursor.executemany("INSERT OR IGNORE INTO hazir_katalog (barkod, urun_adi, kategori) VALUES (?, ?, ?)", hazir_urunler)

    conn.commit()
    conn.close()


init_db()


# 5. ROTALAR (ENDPOINTS)

@app.route("/")
def index():
    return render_template("pos.html")


@app.route("/api/hizli-tuslar")
def get_hizli_tuslar():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.barkod, u.urun_adi, u.birim_fiyat 
        FROM hizli_tuslar h 
        JOIN urunler u ON h.barkod = u.barkod 
        ORDER BY h.sira ASC
    """)
    liste = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(liste)


@app.route("/api/hizli-tus/ekle", methods=["POST"])
def hizli_tus_ekle():
    data = request.get_json()
    barkod = data.get("barkod")
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO hizli_tuslar (barkod) VALUES (?)", (barkod,))
        conn.commit()
        res = {"success": True}
    except Exception:
        res = {"success": False, "message": "Ürün zaten ekli veya bulunamadı."}
    finally:
        conn.close()
    return jsonify(res)


@app.route("/api/hizli-tus/sil", methods=["POST"])
def hizli_tus_sil():
    data = request.get_json()
    barkod = data.get("barkod")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hizli_tuslar WHERE barkod = ?", (barkod,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/kritik-stoklar")
def kritik_stoklar():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urunler WHERE stok_miktari <= kritik_stok ORDER BY stok_miktari ASC")
    liste = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(liste)


@app.route("/api/urun/<barkod>")
def get_urun(barkod):
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Önce dükkandaki aktif ürünler (stok) tablosuna bak
    cursor.execute("SELECT * FROM urunler WHERE barkod = ?", (barkod,))
    urun = cursor.fetchone()
    
    if urun:
        conn.close()
        return jsonify({
            "success": True, 
            "durum": "stokta_var", 
            "urun": dict(urun)
        })
    
    # 2. Stokta yoksa Hazır Katalog tablosunu sorgula
    cursor.execute("SELECT * FROM hazir_katalog WHERE barkod = ?", (barkod,))
    katalog_urun = cursor.fetchone()
    conn.close()
    
    if katalog_urun:
        return jsonify({
            "success": True, 
            "durum": "katalogda_var", 
            "urun": {
                "barkod": katalog_urun["barkod"],
                "urun_adi": katalog_urun["urun_adi"],
                "kategori": katalog_urun["kategori"],
                "birim_fiyat": 0.0,
                "stok_miktari": 0
            }
        })
        
    return jsonify({"success": False, "message": "Ürün bulunamadı!"}), 404

@app.route("/api/satis", methods=["POST"])
def tamamla_satis():
    data = request.get_json()
    sepet = data.get("sepet", [])
    odeme_tipi = data.get("odeme_tipi", "Nakit")
    musteri_id = data.get("musteri_id", None)

    if not sepet:
        return jsonify({"success": False, "message": "Sepet boş!"}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        toplam_tutar = sum(item["fiyat"] * item["adet"] for item in sepet)

        cursor.execute(
            "INSERT INTO satislar (toplam_tutar, odeme_tipi, musteri_id) VALUES (?, ?, ?)",
            (toplam_tutar, odeme_tipi, musteri_id)
        )
        satis_id = cursor.lastrowid

        for item in sepet:
            cursor.execute("""
                INSERT INTO satis_detay (satis_id, barkod, urun_adi, birim_fiyat, adet, toplam)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (satis_id, item["barkod"], item["urun_adi"], item["fiyat"], item["adet"], item["fiyat"] * item["adet"]))

            cursor.execute("UPDATE urunler SET stok_miktari = stok_miktari - ? WHERE barkod = ?", (item["adet"], item["barkod"]))

        if "VERESİYE" in odeme_tipi.upper() and musteri_id:
            cursor.execute("UPDATE musteriler SET bakiye_borc = bakiye_borc + ? WHERE id = ?", (toplam_tutar, musteri_id))
            cursor.execute("""
                INSERT INTO veresiye_hareketleri (musteri_id, islem_tipi, tutar, aciklama)
                VALUES (?, 'BORC', ?, ?)
            """, (musteri_id, toplam_tutar, f"Satış Fiş No: #{satis_id}"))

        conn.commit()
        return jsonify({"success": True, "satis_id": satis_id, "toplam_tutar": toplam_tutar})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@app.route("/veresiye")
def veresiye():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM musteriler ORDER BY bakiye_borc DESC")
    musteriler = cursor.fetchall()
    conn.close()
    return render_template("veresiye.html", musteriler=musteriler)


@app.route("/veresiye/musteri-ekle", methods=["POST"])
def musteri_ekle():
    ad_soyad = request.form.get("ad_soyad")
    telefon = request.form.get("telefon")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO musteriler (ad_soyad, telefon) VALUES (?, ?)", (ad_soyad, telefon))
    conn.commit()
    conn.close()
    flash("Müşteri veresiye defterine eklendi!", "success")
    return redirect(url_for("veresiye"))


@app.route("/veresiye/tahsilat", methods=["POST"])
def veresiye_tahsilat():
    musteri_id = request.form.get("musteri_id")
    tutar = float(request.form.get("tutar", 0))
    odeme_sekli = request.form.get("odeme_sekli", "Nakit")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE musteriler SET bakiye_borc = bakiye_borc - ? WHERE id = ?", (tutar, musteri_id))
    cursor.execute("""
        INSERT INTO veresiye_hareketleri (musteri_id, islem_tipi, tutar, aciklama)
        VALUES (?, 'TAHSILAT', ?, ?)
    """, (musteri_id, tutar, f"Tahsilat ({odeme_sekli})"))
    conn.commit()
    conn.close()
    flash("Tahsilat başarıyla kaydedildi!", "success")
    return redirect(url_for("veresiye"))


@app.route("/toptancilar")
def toptancilar():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM toptancilar ORDER BY id DESC")
    toptanci_listesi = cursor.fetchall()
    cursor.execute("SELECT barkod, urun_adi FROM urunler ORDER BY urun_adi ASC")
    urunler = cursor.fetchall()
    conn.close()
    return render_template("toptancilar.html", toptancilar=toptanci_listesi, urunler=urunler)


@app.route("/toptanci/ekle", methods=["POST"])
def toptanci_ekle():
    firma_adi = request.form.get("firma_adi")
    yetkili = request.form.get("yetkili")
    telefon = request.form.get("telefon")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO toptancilar (firma_adi, yetkili, telefon) VALUES (?, ?, ?)", (firma_adi, yetkili, telefon))
    conn.commit()
    conn.close()
    flash("Toptancı başarıyla eklendi!", "success")
    return redirect(url_for("toptancilar"))


@app.route("/toptanci/mal-alimi", methods=["POST"])
def toptanci_mal_alimi():
    toptanci_id = request.form.get("toptanci_id")
    barkod = request.form.get("barkod", "").strip()
    urun_adi_input = request.form.get("urun_adi_input", "").strip()
    kategori_input = request.form.get("kategori_input", "Genel").strip()
    adet = int(request.form.get("adet", 0))
    alis_fiyati = float(request.form.get("alis_fiyati", 0.0))    # Maliyet
    satis_fiyati = float(request.form.get("satis_fiyati", 0.0))  # Etiket / Satış

    if not toptanci_id or not barkod or adet <= 0:
        flash("Lütfen toptancı, barkod ve geçerli bir adet giriniz!", "danger")
        return redirect(url_for("toptancilar"))

    toplam_maliyet = adet * alis_fiyati

    conn = get_db()
    cursor = conn.cursor()

    # 1. Ürün veritabanında var mı kontrol et
    cursor.execute("SELECT * FROM urunler WHERE barkod = ?", (barkod,))
    mevcut_urun = cursor.fetchone()

    if mevcut_urun:
        # Ürün zaten varsa stok miktarını artır ve yeni satış fiyatını güncelle
        cursor.execute("""
            UPDATE urunler 
            SET stok_miktari = stok_miktari + ?,
                birim_fiyat = ?
            WHERE barkod = ?
        """, (adet, satis_fiyati, barkod))
        kayitli_urun_adi = mevcut_urun["urun_adi"]
    else:
        # Ürün ilk defa giriliyorsa yeni ürün kartı oluştur
        final_urun_adi = urun_adi_input if urun_adi_input else f"Yeni Ürün ({barkod})"
        cursor.execute("""
            INSERT INTO urunler (barkod, urun_adi, birim_fiyat, stok_miktari, kritik_stok, kategori)
            VALUES (?, ?, ?, ?, 5, ?)
        """, (barkod, final_urun_adi, satis_fiyati, adet, kategori_input))
        kayitli_urun_adi = final_urun_adi

    # 2. Toptancının Borç Bakiyesini artır
    cursor.execute("""
        UPDATE toptancilar 
        SET borc_bakiye = borc_bakiye + ? 
        WHERE id = ?
    """, (toplam_maliyet, toptanci_id))

    # 3. Toptancı Hareket Defterine Detaylı Kayıt Ekle
    aciklama = f"Mal Alımı: {kayitli_urun_adi} ({adet} Adet x {alis_fiyati:.2f} TL Maliyet) | Satış Fiyatı: {satis_fiyati:.2f} TL"
    cursor.execute("""
        INSERT INTO toptanci_hareketleri (toptanci_id, islem_tipi, tutar, aciklama)
        VALUES (?, 'MAL_ALIMI', ?, ?)
    """, (toptanci_id, toplam_maliyet, aciklama))

    conn.commit()
    conn.close()

    flash(f"'{kayitli_urun_adi}' ürünü işlendi! Toplam Maliyet: {toplam_maliyet:.2f} TL toptancı borcuna eklendi.", "success")
    return redirect(url_for("toptancilar"))

@app.route("/toptanci/odeme-yap", methods=["POST"])
def toptanci_odeme_yap():
    toptanci_id = request.form.get("toptanci_id")
    tutar = float(request.form.get("tutar", 0))
    odeme_sekli = request.form.get("odeme_sekli", "Nakit")
    aciklama_ek = request.form.get("aciklama", "").strip()

    if tutar <= 0:
        flash("Geçerli bir ödeme tutarı giriniz!", "danger")
        return redirect(url_for("toptancilar"))

    conn = get_db()
    cursor = conn.cursor()

    # 1. Toptancının borç bakiyesinden ödenen tutarı düş
    cursor.execute("UPDATE toptancilar SET borc_bakiye = borc_bakiye - ? WHERE id = ?", (tutar, toptanci_id))

    # 2. Ödeme açıklamasını kurgula
    detay = f"Ödeme Yapıldı ({odeme_sekli})"
    if aciklama_ek:
        detay += f" - {aciklama_ek}"

    # 3. Toptancı hareketler tablosuna ÖDEME kaydı ekle
    cursor.execute("""
        INSERT INTO toptanci_hareketleri (toptanci_id, islem_tipi, tutar, odeme_sekli, aciklama)
        VALUES (?, 'ODEME', ?, ?, ?)
    """, (toptanci_id, tutar, odeme_sekli, detay))

    conn.commit()
    conn.close()

    flash(f"Toptancıya {tutar:.2f} TL tutarında ödeme başarıyla kaydedildi ve borçtan düşüldü.", "success")
    return redirect(url_for("toptancilar"))


@app.route("/urunler")
def urunler():
    search_query = request.args.get('q', '').strip()
    kategori_filter = request.args.get('kategori', '').strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT kategori FROM urunler WHERE kategori IS NOT NULL AND kategori != '' ORDER BY kategori ASC")
    kategoriler = [row['kategori'] for row in cursor.fetchall()]

    sql = "SELECT * FROM urunler WHERE 1=1"
    params = []

    if search_query:
        sql += " AND (barkod LIKE ? OR urun_adi LIKE ? OR kategori LIKE ?)"
        param = f"%{search_query}%"
        params.extend([param, param, param])

    if kategori_filter:
        sql += " AND kategori = ?"
        params.append(kategori_filter)

    sql += " ORDER BY id DESC"

    cursor.execute(sql, params)
    liste = cursor.fetchall()
    conn.close()

    return render_template(
        "products.html",
        urunler=liste,
        kategoriler=kategoriler,
        secili_q=search_query,
        secili_kategori=kategori_filter
    )


@app.route("/urun/ekle", methods=["POST"])
def urun_ekle():
    barkod = request.form.get("barkod").strip()
    urun_adi = request.form.get("urun_adi").strip()
    birim_fiyat = float(request.form.get("birim_fiyat", 0))
    stok_miktari = int(request.form.get("stok_miktari", 0))
    kritik_stok = int(request.form.get("kritik_stok", 5))
    kategori = request.form.get("kategori", "Genel").strip()

    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Önce bu barkodun veritabanında var olup olmadığını kontrol et
    cursor.execute("SELECT id, stok_miktari FROM urunler WHERE barkod = ?", (barkod,))
    mevcut_urun = cursor.fetchone()

    if mevcut_urun:
        # 2. Ürün zaten varsa stok miktarını üzerine ekle (+ stok_miktari)
        yeni_stok = mevcut_urun["stok_miktari"] + stok_miktari
        cursor.execute("""
            UPDATE urunler 
            SET stok_miktari = ?,
                birim_fiyat = ?,
                urun_adi = ?,
                kategori = ?
            WHERE barkod = ?
        """, (yeni_stok, birim_fiyat, urun_adi, kategori, barkod))
        conn.commit()
        flash(f"Mevcut ürüne {stok_miktari} adet ilave edildi. Güncel Stok: {yeni_stok}", "success")
    else:
        # 3. Ürün ilk defa giriliyorsa sıfırdan kaydet
        cursor.execute("""
            INSERT INTO urunler (barkod, urun_adi, birim_fiyat, stok_miktari, kritik_stok, kategori)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (barkod, urun_adi, birim_fiyat, stok_miktari, kritik_stok, kategori))
        conn.commit()
        flash("Yeni ürün başarıyla sisteme eklendi!", "success")

    conn.close()
    return redirect(url_for("urunler"))


@app.route("/urun/excel-yukle", methods=["POST"])
def excel_yukle():
    if 'file' not in request.files:
        flash("Lütfen bir dosya seçin!", "danger")
        return redirect(url_for("urunler"))

    file = request.files['file']
    if file.filename == '':
        flash("Dosya seçilmedi!", "danger")
        return redirect(url_for("urunler"))

    conn = get_db()
    cursor = conn.cursor()
    eklenen_sayisi = 0
    guncellenen_sayisi = 0

    try:
        if file.filename.endswith('.xlsx'):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 3 and row[0] is not None:
                    barkod = str(row[0]).strip()
                    urun_adi = str(row[1]).strip() if row[1] is not None else "İsimsiz Ürün"
                    
                    try:
                        birim_fiyat = float(row[2]) if row[2] is not None else 0.0
                    except ValueError:
                        birim_fiyat = 0.0

                    stok = 0
                    if len(row) > 3 and row[3] is not None and str(row[3]).strip() != "":
                        try:
                            stok = int(float(row[3]))
                        except ValueError:
                            stok = 0

                    kategori = str(row[4]).strip() if len(row) > 4 and row[4] is not None else "Genel"

                    # 1. Ürün veritabanında var mı kontrol et (SQL HATASI DÜZELTİLDİ)
                    cursor.execute("SELECT id, stok_miktari FROM urunler WHERE barkod = ?", (barkod,))
                    mevcut = cursor.fetchone()

                    if mevcut:
                        # Varsa stoğun üzerine EKLE (+ stok) ve bilgileri güncelle
                        yeni_stok = mevcut["stok_miktari"] + stok
                        cursor.execute("""
                            UPDATE urunler 
                            SET stok_miktari = ?, birim_fiyat = ?, urun_adi = ?, kategori = ?
                            WHERE barkod = ?
                        """, (yeni_stok, birim_fiyat, urun_adi, kategori, barkod))
                        guncellenen_sayisi += 1
                    else:
                        # Yoksa sıfırdan ekle
                        cursor.execute("""
                            INSERT INTO urunler (barkod, urun_adi, birim_fiyat, stok_miktari, kritik_stok, kategori)
                            VALUES (?, ?, ?, ?, 5, ?)
                        """, (barkod, urun_adi, birim_fiyat, stok, kategori))
                        eklenen_sayisi += 1

        elif file.filename.endswith('.csv'):
            stream = file.stream.read().decode("utf-8").splitlines()
            csv_reader = csv.reader(stream)
            next(csv_reader, None)
            
            for row in csv_reader:
                if row and len(row) >= 3 and row[0].strip() != "":
                    barkod = row[0].strip()
                    urun_adi = row[1].strip()
                    
                    try:
                        fiyat = float(row[2])
                    except ValueError:
                        fiyat = 0.0

                    stok = 0
                    if len(row) > 3 and row[3].strip() != "":
                        try:
                            stok = int(float(row[3]))
                        except ValueError:
                            stok = 0

                    kategori = row[4].strip() if len(row) > 4 and row[4].strip() != "" else "Genel"

                    cursor.execute("SELECT id, stok_miktari FROM urunler WHERE barkod = ?", (barkod,))
                    mevcut = cursor.fetchone()

                    if mevcut:
                        yeni_stok = mevcut["stok_miktari"] + stok
                        cursor.execute("""
                            UPDATE urunler 
                            SET stok_miktari = ?, birim_fiyat = ?, urun_adi = ?, kategori = ?
                            WHERE barkod = ?
                        """, (yeni_stok, fiyat, urun_adi, kategori, barkod))
                        guncellenen_sayisi += 1
                    else:
                        cursor.execute("""
                            INSERT INTO urunler (barkod, urun_adi, birim_fiyat, stok_miktari, kritik_stok, kategori)
                            VALUES (?, ?, ?, ?, 5, ?)
                        """, (barkod, urun_adi, fiyat, stok, kategori))
                        eklenen_sayisi += 1

        conn.commit()
        toplam_islem = eklenen_sayisi + guncellenen_sayisi
        if toplam_islem > 0:
            flash(f"İşlem Başarılı! {eklenen_sayisi} yeni ürün eklendi, {guncellenen_sayisi} mevcut ürünün stoğu güncellendi/artırıldı.", "success")
        else:
            flash("Uyarı: Dosyada işlenecek uygun veri bulunamadı.", "warning")
            
    except Exception as e:
        conn.rollback()
        flash(f"Dosya okuma hatası: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("urunler"))
@app.route("/raporlar")
def raporlar():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(toplam_tutar), 0) FROM satislar")
    toplam_satis_sayisi, toplam_ciro = cursor.fetchone()

    cursor.execute("SELECT odeme_tipi, SUM(toplam_tutar) FROM satislar GROUP BY odeme_tipi")
    odeme_dagilimi = cursor.fetchall()

    cursor.execute("SELECT * FROM satislar ORDER BY id DESC LIMIT 20")
    son_satislar = cursor.fetchall()

    conn.close()
    return render_template("reports.html",
                           toplam_satis=toplam_satis_sayisi,
                           toplam_ciro=toplam_ciro,
                           odeme_dagilimi=odeme_dagilimi,
                           son_satislar=son_satislar)


@app.route("/api/musteriler")
def get_musteriler():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ad_soyad, bakiye_borc FROM musteriler ORDER BY ad_soyad ASC")
    liste = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(liste)

@app.route("/api/toptanci/<int:toptanci_id>")
def get_toptanci_detay(toptanci_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Toptancı bilgilerini çek
    cursor.execute("SELECT * FROM toptancilar WHERE id = ?", (toptanci_id,))
    toptanci = cursor.fetchone()
    
    if not toptanci:
        conn.close()
        return jsonify({"success": False, "message": "Toptancı bulunamadı"}), 404
        
    # 2. Toptancının alım ve ödeme geçmişini çek
    cursor.execute("""
        SELECT * FROM toptanci_hareketleri 
        WHERE toptanci_id = ? 
        ORDER BY id DESC
    """, (toptanci_id,))
    hareketler = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        "success": True,
        "toptanci": dict(toptanci),
        "hareketler": hareketler
    })
if __name__ == "__main__":
    app.run(debug=True, port=5000)