# Contributing to Xenonite Stack

Terima kasih atas ketertarikan Anda untuk berkontribusi pada **Xenonite Stack**! Proyek ini dibangun dengan semangat open-source untuk menghadirkan arsitektur MCP 4-layer yang self-hosted, hemat token, dan deterministik bagi seluruh developer lintas platform.

---

## Cara Mulai Berkontribusi

1. **Fork Repositori** di [GitHub Muhammad-Rizqullah-Akbar/xenonite-stack](https://github.com/Muhammad-Rizqullah-Akbar/xenonite-stack).
2. **Clone ke Lokal:**
   ```bash
   git clone https://github.com/<username-anda>/xenonite-stack.git
   cd xenonite-stack
   ```
3. **Setup Environment Pengembangan:**
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # Linux/macOS: source .venv/bin/activate
   pip install -e ".[dev]"
   ```
4. **Buat Branch Fitur:**
   ```bash
   git checkout -b feature/nama-fitur
   ```
5. **Jalankan Verifikasi & Unit Test (Zero Regression):**
   ```bash
   xenonite verify --mode all
   python -m unittest discover -s tests -p "test_*.py" -v
   ```
6. **Kirim Pull Request (PR)** dengan deskripsi perubahan yang jelas dan ringkas.

---

## Standar Kode & Keamanan

- **Modularitas:** Pisahkan setiap tanggung jawab berdasarkan layer (`layer1_memory.py`, `layer2_intel.py`, `layer3_code_intel.py`, `layer4_execution.py`, `hooks/`, `cli/`).
- **Zero Hardcoded Paths & Secrets:** Seluruh URL, token, dan path lokal wajib menggunakan environment variables melalui `XenoniteSettings`.
- **Fail-Open Hooks:** Setiap hook pada `xenonite_stack/hooks/` wajib selalu mengeluarkan JSON valid dan tidak pernah memblokir sesi saat terjadi exception tak terduga.
- **Zero Em-Dash Compliance:** Hindari karakter em-dash (U+2014) dan en-dash (U+2013) di seluruh kode dan dokumentasi; gunakan `-` atau `:`.

---

## Area Kontribusi yang Disambut

- **Adapter IDE Baru:** Penambahan auto-installer untuk Claude Code, Cursor, Windsurf, Zed, atau Neovim MCP.
- **Layer 1 Embedding Providers:** Dukungan opsional untuk Ollama embeddings (`/api/embeddings`) atau OpenAI-compatible embeddings selain HuggingFace TEI.
- **Layer 3 Polyglot Graphs:** Ekstensi analisis dependensi modul untuk Python, Rust, dan Go di samping Madge untuk JS/TS.
- **Benchmarking Suite:** Pengukuran kuantitatif penghematan token dan jumlah turn antara workflow standar vs Xenonite 4-Layer.

---

## Kontak

- **GitHub Issues:** [Issue Tracker](https://github.com/Muhammad-Rizqullah-Akbar/xenonite-stack/issues)
- **GitHub Discussions:** [Discussions](https://github.com/Muhammad-Rizqullah-Akbar/xenonite-stack/discussions)
- **Email Maintainer:** `inirizqullahakbar@gmail.com`
