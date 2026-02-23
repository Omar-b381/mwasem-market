import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import sys
import pathlib
import pandas as pd
import sqlite3

try:
    from weasyprint import HTML
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class InvoiceAppTab:
    def __init__(self, parent_frame):
        self.frame = parent_frame
        
        self.COMPANY_DATA = {
            "name": "مواسم الخيرات",
            "address": "9 على رمضان اغا من شارع الجامع عزبة النخل خلف سنتر شاهين بجوار صيدلية العزبي",
            "tax_id": "765-350-577",
            "comm_id": "94591"
        }

        # قائمة المنتجات الافتراضية
        self.PRODUCTS_LIST = [
            "زيتون أخضر سليم",
            "زيتون أخضر مخلي",
            "زيتون أخضر شرائح",
            "زيتون دولسي",
            "زيتون كلاماتا (يوناني)",
            "فلفل هلابينو"
        ]

        # قائمة الوحدات والأحجام
        self.UNITS_LIST = [
            "كجم", "جردل", "720 جرام", "370 جرام", 
            "عدد", "قطعة", "علبة", "طن"
        ]

        self._init_db()
        self._setup_ui()

    def _init_db(self):
        """إنشاء قاعدة البيانات والجداول"""
        conn = sqlite3.connect('invoices_database.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS invoices
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      client_name TEXT,
                      client_address TEXT,
                      client_phone TEXT,
                      invoice_date TEXT,
                      grand_total REAL)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS invoice_items
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      invoice_id INTEGER,
                      item_name TEXT,
                      unit TEXT,
                      qty REAL,
                      price REAL,
                      total REAL,
                      FOREIGN KEY(invoice_id) REFERENCES invoices(id))''')
        
        conn.commit()
        conn.close()

    def _setup_ui(self):
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)

        # --- 1. الهيدر (بيانات العميل) ---
        header_frame = ctk.CTkFrame(self.frame)
        header_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # الصف الأول
        ctk.CTkLabel(header_frame, text="اسم العميل:").grid(row=0, column=0, padx=5, pady=5)
        self.client_entry = ctk.CTkEntry(header_frame, width=250)
        self.client_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(header_frame, text="التاريخ:").grid(row=0, column=2, padx=5, pady=5)
        self.date_entry = ctk.CTkEntry(header_frame, width=150)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # الصف الثاني
        ctk.CTkLabel(header_frame, text="العنوان:").grid(row=1, column=0, padx=5, pady=5)
        self.address_entry = ctk.CTkEntry(header_frame, width=250)
        self.address_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(header_frame, text="رقم الهاتف:").grid(row=1, column=2, padx=5, pady=5)
        self.phone_entry = ctk.CTkEntry(header_frame, width=150)
        self.phone_entry.grid(row=1, column=3, padx=5, pady=5)

        # زر استيراد إكسيل
        ctk.CTkButton(header_frame, text="📂 استيراد من Excel", 
                      command=self.import_from_excel, fg_color="#27ae60").grid(row=1, column=4, padx=15, pady=5)

        # --- 2. قسم الإدخال اليدوي ---
        input_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=2)

        # تحويل اسم الصنف لقائمة منسدلة
        self.entry_item = ctk.CTkComboBox(input_frame, values=self.PRODUCTS_LIST)
        self.entry_item.grid(row=0, column=0, padx=2, sticky="ew")
        self.entry_item.set("") # تفريغ الخانة في البداية

        # القائمة المنسدلة للوحدات والأحجام
        self.entry_unit = ctk.CTkComboBox(input_frame, values=self.UNITS_LIST, width=100)
        self.entry_unit.grid(row=0, column=1, padx=2)
        self.entry_unit.set("كجم") # جعل الكيلوجرام هو الافتراضي

        self.entry_qty = ctk.CTkEntry(input_frame, placeholder_text="الكمية", width=80)
        self.entry_qty.grid(row=0, column=2, padx=2)

        self.entry_price = ctk.CTkEntry(input_frame, placeholder_text="السعر", width=80)
        self.entry_price.grid(row=0, column=3, padx=2)

        ctk.CTkButton(input_frame, text="⬇️ إضافة", width=80, command=self.add_manual_item).grid(row=0, column=4, padx=5)
        ctk.CTkButton(input_frame, text="❌ حذف المحدد", width=80, fg_color="#c0392b", command=self.delete_selected_row).grid(row=0, column=5, padx=2)

        # --- 3. الجدول ---
        table_frame = ctk.CTkFrame(self.frame)
        table_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        columns = ("item", "unit", "qty", "price", "total")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("item", text="اسم الصنف", anchor="w")
        self.tree.heading("unit", text="الوحدة/الحجم", anchor="center")
        self.tree.heading("qty", text="الكمية", anchor="center")
        self.tree.heading("price", text="سعر الوحدة", anchor="center")
        self.tree.heading("total", text="الإجمالي", anchor="center")
        
        self.tree.column("item", width=300, anchor="w")
        self.tree.column("unit", width=100, anchor="center")
        self.tree.column("qty", width=80, anchor="center")
        self.tree.column("price", width=100, anchor="center")
        self.tree.column("total", width=120, anchor="center")
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- 4. الفوتر ---
        footer_frame = ctk.CTkFrame(self.frame)
        footer_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        self.total_label = ctk.CTkLabel(footer_frame, text="الإجمالي النهائي: 0.00 ج", font=ctk.CTkFont(size=20, weight="bold"), text_color="#27ae60")
        self.total_label.pack(side="left", padx=20)
        
        ctk.CTkButton(footer_frame, text="🖨️ طباعة الفاتورة", command=self.generate_pdf, width=150, fg_color="#2980b9").pack(side="right", padx=5)
        ctk.CTkButton(footer_frame, text="💾 حفظ في القاعدة", command=self.save_to_db, width=150, fg_color="#8e44ad").pack(side="right", padx=5)
        ctk.CTkButton(footer_frame, text="🗑️ مسح الكل", command=self.clear_all, width=100, fg_color="#e74c3c").pack(side="right", padx=5)

    def save_to_db(self):
        client = self.client_entry.get().strip()
        address = self.address_entry.get().strip()
        phone = self.phone_entry.get().strip()
        date = self.date_entry.get().strip()

        if not client:
            messagebox.showwarning("تنبيه", "يرجى إدخال اسم العميل قبل الحفظ.")
            return

        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("تنبيه", "الفاتورة فارغة، يرجى إدخال أصناف أولاً.")
            return

        grand_total = 0.0
        for child in items:
            val = self.tree.item(child)['values']
            total_str = str(val[4]).replace(',', '') 
            grand_total += float(total_str)

        try:
            conn = sqlite3.connect('invoices_database.db')
            c = conn.cursor()
            
            c.execute("INSERT INTO invoices (client_name, client_address, client_phone, invoice_date, grand_total) VALUES (?, ?, ?, ?, ?)",
                      (client, address, phone, date, grand_total))
            
            invoice_id = c.lastrowid
            
            for child in items:
                val = self.tree.item(child)['values']
                item_name = val[0]
                unit = val[1]
                qty = float(val[2])
                price = float(str(val[3]).replace(',', ''))
                total = float(str(val[4]).replace(',', ''))
                
                c.execute("INSERT INTO invoice_items (invoice_id, item_name, unit, qty, price, total) VALUES (?, ?, ?, ?, ?, ?)",
                          (invoice_id, item_name, unit, qty, price, total))
            
            conn.commit()
            conn.close()
            messagebox.showinfo("نجاح", f"تم حفظ الفاتورة للعميل ({client}) بنجاح! رقم الفاتورة: {invoice_id}")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء الحفظ:\n{e}")

    def add_manual_item(self):
        item = self.entry_item.get()
        unit = self.entry_unit.get()
        qty_str = self.entry_qty.get()
        price_str = self.entry_price.get()

        if not item or not qty_str or not price_str:
            messagebox.showwarning("تنبيه", "يرجى ملء جميع البيانات (الصنف، الكمية، السعر)")
            return

        try:
            qty = float(qty_str)
            price = float(price_str)
            total = qty * price
            self.tree.insert("", "end", values=(item, unit, qty, f"{price:,.2f}", f"{total:,.2f}"))
            
            # تفريغ الخانات استعداداً للصنف التالي
            self.entry_item.set("") # تفريغ القائمة المنسدلة
            self.entry_qty.delete(0, 'end')
            self.entry_price.delete(0, 'end')
            
            self.update_total_label()
        except ValueError:
            messagebox.showerror("خطأ", "الكمية والسعر يجب أن يكونا أرقاماً.")

    def delete_selected_row(self):
        selected_item = self.tree.selection()
        if selected_item:
            self.tree.delete(selected_item)
            self.update_total_label()
        else:
            messagebox.showinfo("تنبيه", "اختر صنفاً من الجدول لحذفه.")

    def clear_all(self):
        if messagebox.askyesno("تأكيد", "هل أنت متأكد من مسح الفاتورة بالكامل؟"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.client_entry.delete(0, 'end')
            self.address_entry.delete(0, 'end')
            self.phone_entry.delete(0, 'end')
            self.entry_item.set("")
            self.update_total_label()

    def update_total_label(self):
        grand_total = 0.0
        for child in self.tree.get_children():
            val = self.tree.item(child)['values']
            total_str = str(val[4]).replace(',', '') 
            grand_total += float(total_str)
        self.total_label.configure(text=f"الإجمالي النهائي: {grand_total:,.2f} ج")

    def import_from_excel(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx;*.xls")])
        if not file_path:
            return
        try:
            df = pd.read_excel(file_path)
            success_count = 0
            for index, row in df.iterrows():
                try:
                    item_name = str(row.iloc[0])
                    if item_name == "nan" or not item_name.strip(): continue 
                    unit = str(row.iloc[1]) if len(row) > 1 else "عدد"
                    qty = float(row.iloc[2]) if len(row) > 2 else 0
                    price = float(row.iloc[3]) if len(row) > 3 else 0
                    total = qty * price
                    self.tree.insert("", "end", values=(item_name, unit, qty, f"{price:,.2f}", f"{total:,.2f}"))
                    success_count += 1
                except:
                    continue
            self.update_total_label()
            messagebox.showinfo("تم", f"تم استيراد {success_count} صنف بنجاح.")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل القراءة: {e}")

    def generate_pdf(self):
        if not PDF_AVAILABLE:
            messagebox.showerror("خطأ", "مكتبة الطباعة غير متوفرة.")
            return

        client = self.client_entry.get().strip()
        address = self.address_entry.get().strip()
        phone = self.phone_entry.get().strip()
        date = self.date_entry.get().strip()
        
        items_rows = ""
        grand_total = 0
        
        for child in self.tree.get_children():
            vals = self.tree.item(child)['values']
            items_rows += f"""
            <tr>
                <td>{vals[0]}</td>
                <td style="text-align:center">{vals[1]}</td>
                <td style="text-align:center">{vals[2]}</td>
                <td style="text-align:center">{vals[3]}</td>
                <td style="text-align:center">{vals[4]}</td>
            </tr>
            """
            grand_total += float(str(vals[4]).replace(',', ''))

        html_content = self._get_html_template()
        html_content = html_content.replace("{{company_name}}", self.COMPANY_DATA["name"])
        html_content = html_content.replace("{{tax_info}}", f"س.ت: {self.COMPANY_DATA['comm_id']} | ب.ض: {self.COMPANY_DATA['tax_id']}")
        html_content = html_content.replace("{{address}}", self.COMPANY_DATA["address"])
        html_content = html_content.replace("{{client_name}}", client if client else "غير محدد")
        html_content = html_content.replace("{{client_address}}", address if address else "غير محدد")
        html_content = html_content.replace("{{client_phone}}", phone if phone else "غير محدد")
        html_content = html_content.replace("{{date}}", date)
        html_content = html_content.replace("{{items_rows}}", items_rows)
        html_content = html_content.replace("{{grand_total}}", f"{grand_total:,.2f}")

        if getattr(sys, 'frozen', False): base = sys._MEIPASS
        else: base = os.path.dirname(os.path.abspath(__file__))
        
        if os.path.exists(os.path.join(base, "logo.png")):
            logo_uri = pathlib.Path(os.path.join(base, "logo.png")).resolve().as_uri()
            html_content = html_content.replace("logo.png", logo_uri)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_client_name = "".join(x for x in client if x.isalnum() or x.isspace()).strip() if client else "Invoice"
        filename = f"Invoice_{safe_client_name}_{timestamp}.pdf"
        
        try:
            HTML(string=html_content, base_url=base).write_pdf(filename)
            try: os.startfile(filename)
            except: pass
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الطباعة: {e}")

    def _get_html_template(self):
        return """
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                @page { size: A4; margin: 2cm; }
                body { font-family: 'Tahoma', sans-serif; color: #333; }
                .header-table { width: 100%; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
                .company-name { font-size: 24px; font-weight: bold; color: #2c3e50; }
                .tax-info { font-size: 12px; color: #777; }
                .invoice-title { text-align: center; font-size: 20px; background: #f8f9fa; padding: 5px; margin: 20px 0; border: 1px solid #ddd; }
                .client-box { border: 1px solid #eee; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
                .items-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                .items-table th { background: #2c3e50; color: white; padding: 8px; border: 1px solid #2c3e50; }
                .items-table td { padding: 8px; border: 1px solid #ddd; }
                .total-box { text-align: left; margin-top: 20px; font-size: 18px; font-weight: bold; }
            </style>
        </head>
        <body>
            <table class="header-table">
                <tr>
                    <td style="text-align: right">
                        <div class="company-name">{{company_name}}</div>
                        <div class="tax-info">{{tax_info}}</div>
                        <div class="tax-info">{{address}}</div>
                    </td>
                    <td style="text-align: left">
                        <img src="logo.png" style="max-height: 80px;">
                    </td>
                </tr>
            </table>

            <div class="invoice-title">فاتورة مبيعات</div>

            <div class="client-box">
                <table style="width: 100%">
                    <tr>
                        <td style="width: 50%"><strong>العميل:</strong> {{client_name}}</td>
                        <td style="width: 50%"><strong>التاريخ:</strong> {{date}}</td>
                    </tr>
                    <tr>
                        <td><strong>العنوان:</strong> {{client_address}}</td>
                        <td><strong>رقم الهاتف:</strong> {{client_phone}}</td>
                    </tr>
                </table>
            </div>

            <table class="items-table">
                <thead>
                    <tr>
                        <th>الصنف</th>
                        <th>الوحدة</th>
                        <th>الكمية</th>
                        <th>السعر</th>
                        <th>الإجمالي</th>
                    </tr>
                </thead>
                <tbody>
                    {{items_rows}}
                </tbody>
            </table>

            <div class="total-box">
                الإجمالي النهائي: {{grand_total}} ج.م
            </div>
        </body>
        </html>
        """

if __name__ == "__main__":
    ctk.set_appearance_mode("Light") 
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("برنامج فواتير مواسم الخيرات")
    app.geometry("900x650")

    main_container = ctk.CTkFrame(app)
    main_container.pack(fill="both", expand=True, padx=10, pady=10)

    invoice_app = InvoiceAppTab(main_container)

    app.mainloop()