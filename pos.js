let sepet = [];
let islemModu = 'satis';
let iskontoOrani = 0;
let seciliMusteriId = null;

const barcodeInput = document.getElementById('barcode-input');
const alinanParaInput = document.getElementById('alinan-para');

function focusBarcode() {
    if (barcodeInput && document.activeElement !== alinanParaInput) {
        barcodeInput.focus();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    focusBarcode();
    hizliTuslariYukle();
    kritikStoklariKontrolEt();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'F2') {
        e.preventDefault();
        satisiTamamla('Nakit');
    } else if (e.key === 'F3') {
        e.preventDefault();
        satisiTamamla('Kredi Kartı');
    } else if (e.key === 'F5') {
        e.preventDefault();
        veresiyeSatisModalAc();
    } else if (e.key === 'F9') {
        e.preventDefault();
        const yeniMod = islemModu === 'satis' ? 'iade' : 'satis';
        document.getElementById(yeniMod === 'satis' ? 'modSatis' : 'modIade').checked = true;
        modDegistir(yeniMod);
    } else if (e.key === 'F11') {
        e.preventDefault();
        if (alinanParaInput) alinanParaInput.focus();
    }
});

if (barcodeInput) {
    barcodeInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const barkod = this.value.trim();
            if (barkod !== '') {
                barkodAraVeEkle(barkod);
                this.value = '';
            }
        }
    });
}

function kritikStoklariKontrolEt() {
    fetch('/api/kritik-stoklar')
        .then(res => res.json())
        .then(liste => {
            if (liste.length > 0) {
                const banner = document.getElementById('kritik-stok-alert');
                const text = document.getElementById('kritik-stok-text');
                const urunAdlari = liste.map(u => `${u.urun_adi} (Kalan: ${u.stok_miktari})`).join(', ');
                text.innerText = `Şu ürünlerin stoğu tükenmek üzere: ${urunAdlari}`;
                banner.classList.remove('d-none');
            }
        });
}

function hizliTuslariYukle() {
    fetch('/api/hizli-tuslar')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById('touch-grid-container');
            const modalList = document.getElementById('hizli-tus-listesi');
            container.innerHTML = '';
            modalList.innerHTML = '';

            data.forEach(u => {
                // Ana Ekrana Ekle
                container.innerHTML += `
                    <button class="btn btn-touch" onclick="barkodAraVeEkle('${u.barkod}')">
                        ${u.urun_adi}<br><span class="price">${u.birim_fiyat.toFixed(2)} ₺</span>
                    </button>
                `;

                // Modal Listesine Ekle
                modalList.innerHTML += `
                    <li class="list-group-item d-flex justify-content-between align-items-center">
                        ${u.urun_adi} (${u.barkod})
                        <button class="btn btn-sm btn-outline-danger" onclick="hizliTusSil('${u.barkod}')"><i class="bi bi-trash"></i> Sil</button>
                    </li>
                `;
            });
        });
}

function hizliTusEkle() {
    const barkod = document.getElementById('hizli-tus-barkod-input').value.trim();
    if (!barkod) return;

    fetch('/api/hizli-tus/ekle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barkod: barkod })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('hizli-tus-barkod-input').value = '';
                hizliTuslariYukle();
            } else {
                alert(data.message);
            }
        });
}

function hizliTusSil(barkod) {
    fetch('/api/hizli-tus/sil', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barkod: barkod })
    })
        .then(res => res.json())
        .then(() => hizliTuslariYukle());
}

function modDegistir(mod) {
    islemModu = mod;
    const badge = document.getElementById('mod-badge');
    if (mod === 'iade') {
        badge.className = 'badge bg-danger ms-2';
        badge.innerText = 'İADE MODU';
    } else {
        badge.className = 'badge bg-success ms-2';
        badge.innerText = 'SATIŞ MODU';
    }
    sepetiGuncelle();
}

function barkodAraVeEkle(barkod) {
    fetch(`/api/urun/${barkod}`)
        .then(res => {
            if (!res.ok) {
                throw new Error("Ürün bulunamadı!");
            }
            return res.json();
        })
        .then(data => {
            if (data.success) {
                if (data.durum === "stokta_var") {
                    // 1. Ürün zaten stokta kayıtlıysa doğrudan sepete ekle
                    sepeteEkleObj(data.urun);
                }
                else if (data.durum === "katalogda_var") {
                    // 2. Ürün hazır katalogda var ama stokta yoksa kullanıcıdan fiyat ve stok iste
                    katalogUrunuTanimlaVeEkle(data.urun);
                }
            }
        })
        .catch(err => {
            alert("Hata: Bu barkod ne stoğunuzda ne de hazır katalogda bulunamadı!");
            focusBarcode();
        });
}

// Katalogdan gelen ürünü stoğa tanımlayıp sepete atan yardımcı fonksiyon
function katalogUrunuTanimlaVeEkle(urun) {
    // Fiyat İste
    const fiyatInput = prompt(
        `📦 ÜRÜN HAZIR KATALOGDA BULUNDU!\n\n` +
        `Ürün Adı: ${urun.urun_adi}\n` +
        `Kategori: ${urun.kategori}\n\n` +
        `Lütfen bu ürün için SATIŞ FİYATINI (TL) girin:`,
        "15.00"
    );

    if (fiyatInput === null) {
        focusBarcode();
        return; // Kullanıcı iptal etti
    }

    const fiyat = parseFloat(fiyatInput.replace(',', '.'));
    if (isNaN(fiyat) || fiyat <= 0) {
        alert("Geçersiz fiyat girdiniz!");
        focusBarcode();
        return;
    }

    // Stok Miktarı İste
    const stokInput = prompt(`"${urun.urun_adi}" için BAŞLANGIÇ STOK MİKTARINI girin:`, "50");
    const stok = parseInt(stokInput);
    if (isNaN(stok) || stok < 0) {
        alert("Geçersiz stok miktarı girdiniz!");
        focusBarcode();
        return;
    }

    // Form Verisi Oluşturup /urun/ekle Rotasına Gönder
    const formData = new FormData();
    formData.append("barkod", urun.barkod);
    formData.append("urun_adi", urun.urun_adi);
    formData.append("birim_fiyat", fiyat);
    formData.append("stok_miktari", stok);
    formData.append("kritik_stok", 5);
    formData.append("kategori", urun.kategori);

    fetch("/urun/ekle", {
        method: "POST",
        body: formData
    })
        .then(res => {
            if (res.ok) {
                // Veritabanına kaydedildi, nesneyi güncelleyip sepete ekle
                urun.birim_fiyat = fiyat;
                urun.stok_miktari = stok;

                sepeteEkleObj(urun);
                alert(`"${urun.urun_adi}" başarıyla stoğunuza kaydedildi ve sepete eklendi!`);
            } else {
                alert("Ürün kaydedilirken bir hata oluştu!");
            }
        })
        .catch(err => {
            alert("Bağlantı hatası oluştu!");
        })
        .finally(() => {
            focusBarcode();
        });
}

// Sepete ürün nesnesi ekleme yardımcısı (Eğer projenizde farklı bir fonksiyon adı varsa burayı güncelleyebilirsiniz)
function sepeteEkleObj(urun) {
    const varolanIndex = sepet.findIndex(item => item.barkod === urun.barkod);

    if (varolanIndex > -1) {
        sepet[varolanIndex].adet += 1;
    } else {
        sepet.push({
            barkod: urun.barkod,
            urun_adi: urun.urun_adi,
            fiyat: urun.birim_fiyat,
            adet: 1
        });
    }
    sepetiGuncelle();
}

function sepetiGuncelle() {
    const tbody = document.getElementById('cart-table-body');
    tbody.innerHTML = '';

    let hamToplam = 0;

    sepet.forEach((item, index) => {
        const urunToplam = item.fiyat * item.adet;
        hamToplam += urunToplam;

        const tr = document.createElement('tr');
        if (islemModu === 'iade') tr.classList.add('table-danger');

        tr.innerHTML = `
            <td>${index + 1}</td>
            <td><span class="badge bg-secondary font-monospace">${item.barkod}</span></td>
            <td class="fw-bold">${item.urun_adi} ${islemModu === 'iade' ? '(İADE)' : ''}</td>
            <td class="text-center">
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary" onclick="adetDegistir(${index}, -1)">-</button>
                    <span class="btn btn-light disabled fw-bold px-2">${item.adet}</span>
                    <button class="btn btn-outline-secondary" onclick="adetDegistir(${index}, 1)">+</button>
                </div>
            </td>
            <td class="text-end">${item.fiyat.toFixed(2)} ₺</td>
            <td class="text-end fw-bold ${islemModu === 'iade' ? 'text-danger' : 'text-success'}">
                ${islemModu === 'iade' ? '-' : ''}${urunToplam.toFixed(2)} ₺
            </td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-danger" onclick="urunSil(${index})"><i class="bi bi-x-lg"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    let odenecekTutar = hamToplam * (1 - iskontoOrani / 100);
    if (islemModu === 'iade') odenecekTutar = -odenecekTutar;

    document.getElementById('total-amount').innerText = `${odenecekTutar.toFixed(2)} ₺`;
    paraUstuHesapla();
    focusBarcode();
}

function iskontoUygula() {
    const oran = prompt("İskonto oranını yüzde (%) olarak girin:", "10");
    if (oran !== null && !isNaN(oran)) {
        iskontoOrani = parseFloat(oran);
        sepetiGuncelle();
    }
}

function paraUstuHesapla() {
    const alinan = parseFloat(alinanParaInput.value) || 0;
    const totalText = document.getElementById('total-amount').innerText.replace(' ₺', '');
    const odenecek = parseFloat(totalText) || 0;

    const paraUstu = alinan - odenecek;
    const paraUstuEl = document.getElementById('para-ustu');

    if (paraUstu >= 0 && odenecek > 0) {
        paraUstuEl.innerText = `${paraUstu.toFixed(2)} ₺`;
        paraUstuEl.className = "mb-0 fw-bolder text-success";
    } else {
        paraUstuEl.innerText = "0.00 ₺";
        paraUstuEl.className = "mb-0 fw-bolder text-danger";
    }
}

function veresiyeSatisModalAc() {
    if (sepet.length === 0) {
        alert("Sepette ürün yok!");
        return;
    }
    fetch('/api/musteriler')
        .then(res => res.json())
        .then(musteriler => {
            const select = document.getElementById('veresiye-musteri-select');
            select.innerHTML = '';
            musteriler.forEach(m => {
                select.innerHTML += `<option value="${m.id}">${m.ad_soyad} (Borç: ${m.bakiye_borc.toFixed(2)} ₺)</option>`;
            });
            new bootstrap.Modal(document.getElementById('veresiyeModal')).show();
        });
}

function veresiyeSatisOnayla() {
    const musteriId = document.getElementById('veresiye-musteri-select').value;
    seciliMusteriId = musteriId;
    satisiTamamla('Veresiye Satış', musteriId);
    bootstrap.Modal.getInstance(document.getElementById('veresiyeModal')).hide();
}

function adetDegistir(index, miktar) {
    sepet[index].adet += miktar;
    if (sepet[index].adet <= 0) sepet.splice(index, 1);
    sepetiGuncelle();
}

function urunSil(index) {
    sepet.splice(index, 1);
    sepetiGuncelle();
}

function sepetiTemizle() {
    sepet = [];
    iskontoOrani = 0;
    seciliMusteriId = null;
    if (alinanParaInput) alinanParaInput.value = '';
    sepetiGuncelle();
}

function satisiTamamla(odemeTipi, musteriId = null) {
    if (sepet.length === 0) {
        alert("Sepette ürün yok!");
        return;
    }

    fetch('/api/satis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sepet: sepet,
            odeme_tipi: `${odemeTipi} (${islemModu.toUpperCase()})`,
            musteri_id: musteriId
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert(`İşlem Tamamlandı!
Mod: ${islemModu.toUpperCase()}
Fiş No: #${data.satis_id}
Tutar: ${data.toplam_tutar.toFixed(2)} ₺
Ödeme: ${odemeTipi}`);
                sepetiTemizle();
                kritikStoklariKontrolEt();
            } else {
                alert("Hata: " + data.message);
            }
        })
        .catch(() => alert("Bağlantı hatası!"));
}
