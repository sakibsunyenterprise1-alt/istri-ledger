import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="শাল চাদর ইস্ত্রি খতিয়ান", layout="wide", page_icon="🧣")

# খাঁটি বাংলায় সংখ্যা রূপান্তর
def to_bn(number):
    if number is None or pd.isna(number) or str(number).strip() == "":
        return "০"
    bn_map = {'0':'০', '1':'১', '2':'২', '3':'৩', '4':'৪', '5':'৫', '6':'৬', '7':'৭', '8':'৮', '9':'৯', '.':'.', ',':','}
    if isinstance(number, (int, float)):
        formatted_str = f"{number:,.2f}".rstrip('0').rstrip('.') if isinstance(number, float) else f"{number:,}"
    else:
        formatted_str = str(number)
    return "".join(bn_map.get(c, c) for c in formatted_str)

def get_db():
    conn = sqlite3.connect('istri_ledger.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS workers_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')
    for w in ["সাব্বির", "মাসুদ", "লিটন"]:
        c.execute("INSERT OR IGNORE INTO workers_list (name) VALUES (?)", (w,))

    c.execute('''
    CREATE TABLE IF NOT EXISTS work_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        worker_name TEXT NOT NULL,
        chador_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        rate_per_piece REAL NOT NULL,
        total_bill REAL NOT NULL,
        notes TEXT
    )''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS payment_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        worker_name TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_mode TEXT,
        notes TEXT
    )''')
    conn.commit()
    conn.close()

init_db()
conn = get_db()

# ডেটা ফেচিং
df_work = pd.read_sql_query("SELECT * FROM work_records", conn)
df_pay = pd.read_sql_query("SELECT * FROM payment_records", conn)
workers_df = pd.read_sql_query("SELECT name FROM workers_list", conn)
workers = workers_df['name'].tolist()

st.title("🧣 শাল চাদর ইস্ত্রি হিসাব খতিয়ান")

# --- ওপরে কর্মীর নাম ড্রপডাউন ---
if 'active_worker' not in st.session_state:
    st.session_state.active_worker = workers[0]

selected_worker = st.selectbox(
    "📌 কর্মী নির্বাচন করুন:", 
    workers, 
    index=workers.index(st.session_state.active_worker) if st.session_state.active_worker in workers else 0,
    key="top_worker_selector"
)
st.session_state.active_worker = selected_worker

# নির্বাচিত কর্মীর ডেটা ফিল্টার
disp_work = df_work[df_work['worker_name'] == selected_worker] if not df_work.empty else pd.DataFrame()
disp_pay = df_pay[df_pay['worker_name'] == selected_worker] if not df_pay.empty else pd.DataFrame()

# হিসাব ক্যালকুলেশন
w_ladies_pcs = int(disp_work[disp_work['chador_type'] == 'Ladies']['quantity'].sum()) if not disp_work.empty else 0
w_gents_pcs = int(disp_work[disp_work['chador_type'] == 'Gents']['quantity'].sum()) if not disp_work.empty else 0
w_total_pcs = w_ladies_pcs + w_gents_pcs

w_total_bill = float(disp_work['total_bill'].sum()) if not disp_work.empty else 0.0
w_total_taken = float(disp_pay['amount'].sum()) if not disp_pay.empty else 0.0

# মূল সূত্র: নেওয়া টাকা - কাজের মোট বিল = অবশিষ্ট স্থিতি
rem_balance = w_total_taken - w_total_bill

# --- ওপরে নির্বাচিত কর্মীর ড্যাশবোর্ড কার্ডস ---
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("মোট ইস্ত্রি", f"{to_bn(w_total_pcs)} পিস")
c2.metric("Ladies চাদর", f"{to_bn(w_ladies_pcs)} পিস")
c3.metric("Gents চাদর", f"{to_bn(w_gents_pcs)} পিস")
c4.metric("কাজের মোট বিল", f"৳ {to_bn(w_total_bill)}")
c5.metric("মোট নেওয়া টাকা", f"৳ {to_bn(w_total_taken)}")

if rem_balance > 0:
    c6.metric("অবশিষ্ট অগ্রিম স্থিতি", f"৳ {to_bn(rem_balance)}")
    st.info(f"💡 **হিসাব সূত্র:** নেওয়া টাকা (৳ {to_bn(w_total_taken)}) − কাজের বিল (৳ {to_bn(w_total_bill)}) = **অবশিষ্ট অগ্রিম ৳ {to_bn(rem_balance)}**।")
elif rem_balance < 0:
    c6.metric("বকেয়া মজুরি পাবে", f"৳ {to_bn(abs(rem_balance))}")
    st.success(f"💡 **হিসাব সূত্র:** কাজের বিল (৳ {to_bn(w_total_bill)}) − নেওয়া টাকা (৳ {to_bn(w_total_taken)}) = **মজুরি বকেয়া পাবে ৳ {to_bn(abs(rem_balance))}**।")
else:
    c6.metric("অবশিষ্ট স্থিতি", "০ ৳")
    st.write(f"✅ **{selected_worker}**-এর নেওয়া টাকা ও কাজের বিল সমান।")

st.markdown("---")

# ট্যাবস
tab_work_entry, tab_pay_entry, tab_worker_details, tab_all_table, tab_worker_add, tab_manage = st.tabs([
    f"🧺 ১. {selected_worker}-এর চাদর জমা ও বিল এন্ট্রি",
    f"💵 ২. {selected_worker}-এর নগদ/অগ্রিম এন্ট্রি",
    f"📋 {selected_worker}-এর খতিয়ান বিবরণী",
    "📊 সকল কর্মীর তুলনামূলক তালিকা",
    "➕ নতুন কর্মী যোগ",
    "✏️ সংশোধন ও ডিলিট"
])

today_str = datetime.today().strftime('%d/%m/%Y')

# ----------------- TAB 1: WORK ENTRY -----------------
with tab_work_entry:
    st.subheader(f"🧺 {selected_worker}-এর চাদর ইস্ত্রি জমা ও বিল এন্ট্রি")
    with st.form("form_work_entry", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            in_w_date = st.text_input("তারিখ (দিন/মাস/বছর)", value=today_str)
            st.text_input("কর্মী", value=selected_worker, disabled=True)
            in_w_type = st.selectbox("চাদরের ধরন", ["Ladies", "Gents"])
        with f2:
            in_w_qty = st.number_input("কত পিস জমা দিল?", min_value=0, step=1, value=0)
            in_w_rate = st.number_input("প্রতি পিস মজুরি রেট (৳)", min_value=0.0, step=0.5, value=0.0)
        with f3:
            w_total_calc = in_w_qty * in_w_rate
            st.metric("হিসাবকৃত বিল", f"৳ {to_bn(w_total_calc)}")
            in_w_notes = st.text_input("মন্তব্য / চালান", "")

        if st.form_submit_button("✅ সংরক্ষণ করুন ও ড্যাশবোর্ডে যোগ করুন"):
            if in_w_qty <= 0 or in_w_rate <= 0:
                st.error("অনুগ্রহ করে পিস এবং রেটের সঠিক সংখ্যা লিখুন!")
            else:
                conn_exec = get_db()
                c = conn_exec.cursor()
                c.execute("""
                    INSERT INTO work_records (date, worker_name, chador_type, quantity, rate_per_piece, total_bill, notes)
                    VALUES (?,?,?,?,?,?,?)
                """, (in_w_date, selected_worker, in_w_type, in_w_qty, in_w_rate, w_total_calc, in_w_notes))
                conn_exec.commit()
                conn_exec.close()
                st.success(f"{selected_worker}-এর {in_w_qty} পিস {in_w_type} চাদরের বিল ৳ {to_bn(w_total_calc)} যুক্ত হয়েছে!")
                st.rerun()

# ----------------- TAB 2: PAYMENT ENTRY -----------------
with tab_pay_entry:
    st.subheader(f"💵 {selected_worker}-এর টাকা নেওয়ার (ক্যাশ/অগ্রিম) এন্ট্রি")
    with st.form("form_pay_entry", clear_on_submit=True):
        p1, p2, p3 = st.columns(3)
        with p1:
            in_p_date = st.text_input("তারিখ (দিন/মাস/বছর)", value=today_str, key="pay_entry_d")
            st.text_input("কর্মী", value=selected_worker, disabled=True, key="pay_worker_locked")
        with p2:
            in_p_amount = st.number_input("কত টাকা নিল?", min_value=0.0, step=100.0, value=0.0)
            in_p_mode = st.selectbox("পেমেন্ট মাধ্যম", ["নগদ গ্রহণ", "বিকাশ/নগদ", "ব্যাংক"])
        with p3:
            in_p_notes = st.text_input("মন্তব্য", "")

        if st.form_submit_button("✅ সংরক্ষণ করুন"):
            if in_p_amount <= 0:
                st.error("টাকার সঠিক পরিমাণ লিখুন!")
            else:
                conn_exec = get_db()
                c = conn_exec.cursor()
                c.execute("""
                    INSERT INTO payment_records (date, worker_name, amount, payment_mode, notes)
                    VALUES (?,?,?,?,?)
                """, (in_p_date, selected_worker, in_p_amount, in_p_mode, in_p_notes))
                conn_exec.commit()
                conn_exec.close()
                st.success(f"{selected_worker}-এর ৳ {to_bn(in_p_amount)} নেওয়ার রেকর্ড যুক্ত হয়েছে!")
                st.rerun()

# ----------------- TAB 3: WORKER DETAILS -----------------
with tab_worker_details:
    st.subheader(f"🔍 {selected_worker}-এর খতিয়ান বিবরণী")
    col_w_left, col_w_right = st.columns(2)
    with col_w_left:
        st.markdown(f"**🧺 {selected_worker}-এর চাদর জমার খতিয়ান:**")
        if not disp_work.empty:
            st.dataframe(disp_work[['date', 'chador_type', 'quantity', 'rate_per_piece', 'total_bill', 'notes']].sort_values(by='date', ascending=False), use_container_width=True)
        else:
            st.write("কোনো চাদর জমা দেওয়ার রেকর্ড নেই।")
    with col_w_right:
        st.markdown(f"**💵 {selected_worker}-এর টাকা নেওয়ার খতিয়ান:**")
        if not disp_pay.empty:
            st.dataframe(disp_pay[['date', 'amount', 'payment_mode', 'notes']].sort_values(by='date', ascending=False), use_container_width=True)
        else:
            st.write("কোনো টাকা নেওয়ার রেকর্ড নেই।")

# ----------------- TAB 4: ALL WORKERS TABLE -----------------
with tab_all_table:
    st.subheader("👥 সকল কর্মীর সংক্ষিপ্ত তুলনামূলক হিসাব")
    summary_table = []
    for w in workers:
        sub_w = df_work[df_work['worker_name'] == w] if not df_work.empty else pd.DataFrame()
        sub_p = df_pay[df_pay['worker_name'] == w] if not df_pay.empty else pd.DataFrame()
        
        l_cnt = sub_w[sub_w['chador_type'] == 'Ladies']['quantity'].sum() if not sub_w.empty else 0
        g_cnt = sub_w[sub_w['chador_type'] == 'Gents']['quantity'].sum() if not sub_w.empty else 0
        tot_q = l_cnt + g_cnt
        b_sum = sub_w['total_bill'].sum() if not sub_w.empty else 0
        p_sum = sub_p['amount'].sum() if not sub_p.empty else 0
        
        diff_val = p_sum - b_sum
        if diff_val > 0:
            stat_str = f"৳ {to_bn(diff_val)} (অগ্রিম)"
        elif diff_val < 0:
            stat_str = f"৳ {to_bn(abs(diff_val))} (বকেয়া পাবে)"
        else:
            stat_str = "০ ৳ (সমান)"
            
        summary_table.append({
            "কর্মী": w,
            "Ladies চাদর": f"{to_bn(l_cnt)} পিস",
            "Gents চাদর": f"{to_bn(g_cnt)} পিস",
            "মোট ইস্ত্রি": f"{to_bn(tot_q)} পিস",
            "কাজের মোট বিল": f"৳ {to_bn(b_sum)}",
            "মোট নেওয়া টাকা": f"৳ {to_bn(p_sum)}",
            "অবশিষ্ট স্থিতি (নেওয়া - বিল)": stat_str
        })
    st.dataframe(pd.DataFrame(summary_table), use_container_width=True)

# ----------------- TAB 5: ADD WORKER -----------------
with tab_worker_add:
    st.subheader("➕ নতুন কর্মী যোগ করুন")
    with st.form("form_add_worker", clear_on_submit=True):
        new_w_name = st.text_input("নতুন কর্মীর পুরো নাম")
        if st.form_submit_button("➕ যুক্ত করুন"):
            if new_w_name.strip():
                try:
                    conn_exec = get_db()
                    c = conn_exec.cursor()
                    c.execute("INSERT INTO workers_list (name) VALUES (?)", (new_w_name.strip(),))
                    conn_exec.commit()
                    conn_exec.close()
                    st.success(f"কর্মী '{new_w_name.strip()}' যুক্ত হয়েছে!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.warning("এই নামের কর্মী তালিকায় বিদ্যমান রয়েছে!")
            else:
                st.error("নাম লিখুন!")

# ----------------- TAB 6: EDIT & DELETE -----------------
with tab_manage:
    st.subheader("✏️ ভুল হলে সংশোধন বা ডিলিট করুন")
    target_choice = st.radio("কোন খতিয়ানের ভুল ঠিক করবেন?", ["চাদর জমার বিল খতিয়ান", "টাকা দেওয়া / অগ্রিমের খতিয়ান"], horizontal=True)
    
    if target_choice == "চাদর জমার বিল খতিয়ান":
        if not df_work.empty:
            sel_w_id = st.selectbox("রেকর্ড আইডি বাছুন", df_work['id'].tolist())
            w_cur = df_work[df_work['id'] == sel_w_id].iloc[0]
            with st.form("form_edit_work"):
                ew1, ew2, ew3 = st.columns(3)
                with ew1:
                    new_wd = st.text_input("তারিখ", str(w_cur['date']))
                    new_ww = st.selectbox("কর্মী", workers, index=workers.index(w_cur['worker_name']) if w_cur['worker_name'] in workers else 0)
                    new_wt = st.selectbox("ধরন", ["Ladies", "Gents"], index=0 if w_cur['chador_type']=='Ladies' else 1)
                with ew2:
                    new_wq = st.number_input("পিস সংখ্যা", value=int(w_cur['quantity']), step=1)
                    new_wr = st.number_input("রেট (৳)", value=float(w_cur['rate_per_piece']), step=0.5)
                with ew3:
                    new_wb = new_wq * new_wr
                    st.write(f"নতুন বিল: **৳ {to_bn(new_wb)}**")
                    new_wn = st.text_input("মন্তব্য", str(w_cur['notes']))
                
                b1, b2 = st.columns([1, 4])
                with b1:
                    if st.form_submit_button("✏️ আপডেট করুন"):
                        conn_exec = get_db()
                        c = conn_exec.cursor()
                        c.execute("UPDATE work_records SET date=?, worker_name=?, chador_type=?, quantity=?, rate_per_piece=?, total_bill=?, notes=? WHERE id=?",
                                  (new_wd, new_ww, new_wt, new_wq, new_wr, new_wb, new_wn, sel_w_id))
                        conn_exec.commit()
                        conn_exec.close()
                        st.success("রেকর্ড আপডেট সফল হয়েছে!")
                        st.rerun()
                with b2:
                    if st.form_submit_button("🗑️ মুছে ফেলুন (Delete)"):
                        conn_exec = get_db()
                        c = conn_exec.cursor()
                        c.execute("DELETE FROM work_records WHERE id=?", (sel_w_id,))
                        conn_exec.commit()
                        conn_exec.close()
                        st.warning("রেকর্ডটি মুছে ফেলা হয়েছে!")
                        st.rerun()
    else:
        if not df_pay.empty:
            sel_p_id = st.selectbox("টাকা দেওয়ার রেকর্ড আইডি বাছুন", df_pay['id'].tolist())
            p_cur = df_pay[df_pay['id'] == sel_p_id].iloc[0]
            with st.form("form_edit_pay"):
                ep1, ep2 = st.columns(2)
                with ep1:
                    new_pd = st.text_input("তারিখ", str(p_cur['date']))
                    new_pw = st.selectbox("কর্মী", workers, index=workers.index(p_cur['worker_name']) if p_cur['worker_name'] in workers else 0)
                with ep2:
                    new_pa = st.number_input("টাকার পরিমাণ (৳)", value=float(p_cur['amount']), step=50.0)
                    new_pn = st.text_input("মন্তব্য", str(p_cur['notes']))
                
                b3, b4 = st.columns([1, 4])
                with b3:
                    if st.form_submit_button("✏️ আপডেট করুন"):
                        conn_exec = get_db()
                        c = conn_exec.cursor()
                        c.execute("UPDATE payment_records SET date=?, worker_name=?, amount=?, notes=? WHERE id=?",
                                  (new_pd, new_pw, new_pa, new_pn, sel_p_id))
                        conn_exec.commit()
                        conn_exec.close()
                        st.success("টাকার রেকর্ড আপডেট হয়েছে!")
                        st.rerun()
                with b4:
                    if st.form_submit_button("🗑️ মুছে ফেলুন (Delete)"):
                        conn_exec = get_db()
                        c = conn_exec.cursor()
                        c.execute("DELETE FROM payment_records WHERE id=?", (sel_p_id,))
                        conn_exec.commit()
                        conn_exec.close()
                        st.warning("রেকর্ড মুছে ফেলা হয়েছে!")
                        st.rerun()

conn.close()
