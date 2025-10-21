import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== CONFIGURAÇÕES ==========
BOT_TOKEN = "8464485123:AAGfibOpvx6ASRrcepmQJlZ1GuoAAYml6Ws"
ADMIN_ID = 6995978182
MIN_DEPOSIT = 4.00
BOT_USERNAME = "@JOAOSTORE_BOT"
SUPPORT_USERNAME = "@suporte_joaozinstore"
GROUP_URL = "https://t.me/joaostore_clientes"

# ========== BANCO DE DADOS ==========
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('joao_store.db', check_same_thread=False)
        self.create_tables()
        self.create_sample_products()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                price REAL,
                credentials TEXT,
                status TEXT DEFAULT 'completed'
            )
        ''')
        
        self.conn.commit()
    
    def create_sample_products(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM products')
        if cursor.fetchone()[0] == 0:
            products = [
                ("NETFLIX PREMIUM", "Netflix Premium 4K", 11.00, 50),
                ("MAX HBO", "HBO Max Premium", 3.00, 30),
                ("PRIME VIDEO", "Amazon Prime Video", 3.00, 40),
                ("DISNEY+", "Disney+ Star+", 5.00, 35),
                ("YOUTUBE PREMIUM", "YouTube Premium Familiar", 8.00, 25),
                ("SPOTIFY", "Spotify Premium", 4.00, 20)
            ]
            
            for name, desc, price, stock in products:
                cursor.execute(
                    'INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)',
                    (name, desc, price, stock)
                )
            self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def get_products(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE is_active = TRUE')
        return cursor.fetchall()
    
    def get_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        return cursor.fetchone()
    
    def create_order(self, user_id, product_id, credentials):
        cursor = self.conn.cursor()
        product = self.get_product(product_id)
        cursor.execute(
            'INSERT INTO orders (user_id, product_id, price, credentials) VALUES (?, ?, ?, ?)',
            (user_id, product_id, product[3], credentials)
        )
        cursor.execute('UPDATE products SET stock = stock - 1 WHERE id = ?', (product_id,))
        self.conn.commit()
        return cursor.lastrowid

# ========== INICIALIZAR BANCO ==========
db = Database()

# ========== HANDLERS PRINCIPAIS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    db.add_user(user_id, user.username, user.first_name)
    user_data = db.get_user(user_id)
    balance = user_data[3] if user_data else 0.0
    
    welcome_text = f"""
🥇 *Descubra como nosso bot pode transformar sua experiência de compras!*

*Importante:* Não realizamos reembolsos em dinheiro. Suporte por 48 horas após entrega.

👥 *Grupo De Clientes:* {GROUP_URL}
👨‍💻 *Suporte:* {SUPPORT_USERNAME}

*ℹ️ Seus Dados:*
🆔 *ID:* `{user_id}`
💸 *Saldo Atual:* R${balance:.2f}
🪪 *Usuário:* @{user.username if user.username else 'N/A'}
    """
    
    keyboard = [
        [InlineKeyboardButton("💎 Logins | Contas Premium", callback_data="premium_products")],
        [
            InlineKeyboardButton("🪪 PERFIL", callback_data="profile"),
            InlineKeyboardButton("💰 RECARGA", callback_data="recharge")
        ],
        [
            InlineKeyboardButton("🎖️ Ranking", callback_data="ranking"),
            InlineKeyboardButton("👩‍💻 Suporte", url=SUPPORT_USERNAME)
        ],
        [
            InlineKeyboardButton("ℹ️ Informações", callback_data="info"),
            InlineKeyboardButton("🔎 Pesquisar", callback_data="search")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def premium_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    balance = user[3] if user else 0
    
    products = db.get_products()
    
    text = f"""
🎟️ *Logins Premium | Acesso Exclusivo*

🏦 *Carteira*
💸 *Saldo Atual:* R${balance:.2f}

*Produtos Disponíveis:*
    """
    
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(f"{product[1]} - R${product[3]:.2f}", callback_data=f"product_{product[0]}")
        ])
    
    keyboard.append([InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = db.get_product(product_id)
    user = db.get_user(query.from_user.id)
    balance = user[3] if user else 0
    
    text = f"""
⚜️ *ACESSO:* {product[1]}

💵 *Preço:* R${product[3]:.2f}
💼 *Saldo Atual:* R${balance:.2f}
📥 *Estoque Disponível:* {product[4]}

🗒️ *Descrição:* {product[2]}

*Aviso Importante:*
Acesso liberado na hora. Sem reembolsos em dinheiro, apenas créditos.
Suporte por 48 horas.

♻️ *Garantia:* 30 dias
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🛒 Comprar", callback_data=f"buy_{product_id}"),
            InlineKeyboardButton("↩️ Voltar", callback_data="premium_products")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = db.get_product(product_id)
    user = db.get_user(query.from_user.id)
    
    if user[3] < product[3]:
        missing = product[3] - user[3]
        text = f"*Saldo insuficiente! Faltam R${missing:.2f}*\n\nFaça uma recarga!\n*Seu saldo:* R${user[3]:.2f}"
        
        keyboard = [
            [InlineKeyboardButton("💰 Fazer Recarga", callback_data="recharge")],
            [InlineKeyboardButton("↩️ Voltar", callback_data=f"product_{product_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Processar compra
    credentials = f"email: user{user[0]}@joaostore.com\nsenha: {user[0]}{product_id}123"
    order_id = db.create_order(user[0], product_id, credentials)
    db.update_balance(user[0], -product[3])
    
    text = f"""
✅ *Compra realizada com sucesso!*

📦 *Produto:* {product[1]}
💰 *Valor:* R${product[3]:.2f}
🆔 *Pedido:* #{order_id}

*Credenciais:*
  
♻️ *Garantia:* 30 dias
📞 *Suporte:* {SUPPORT_USERNAME}
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Comprar Novamente", callback_data="premium_products")],
        [InlineKeyboardButton("↩️ Início", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def recharge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    
    text = f"""
💼 *ID da Carteira:* `{user[0]}`
💵 *Saldo Disponível:* R${user[3]:.2f}

💡 *Sistema de Recarga:*
    
⚠️ *Para recarregar, entre em contato com o suporte:*
{SUPPORT_USERNAME}

*Envie seu ID e valor desejado.*
    """
    
    keyboard = [
        [InlineKeyboardButton("👩‍💻 Falar com Suporte", url=SUPPORT_USERNAME)],
        [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    
    text = f"""
🙋‍♂️ *Meu Perfil*

🆔 *ID da Carteira:* `{user[0]}`
💰 *Saldo Atual:* R${user[3]:.2f}

*📊 Movimentações:*
—🛒 *Compras Realizadas:* 0
—💠 *Recargas:* R$0,00
—🎁 *Gifts:* R$0,00
    """
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Histórico", callback_data="history")],
        [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""
ℹ️ *SOFTWARE INFO:*
🤖 *BOT:* {BOT_USERNAME}
🤖 *VERSION:* 2.0

🛠️ *DESENVOLVEDOR:*
Não possui responsabilidade sobre conteúdo.
Apenas para conhecer outros bots.
    """
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🏆 *Ranking - Em Desenvolvimento*

🔜 *Em breve rankings completos!*
    """
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🔎 *Pesquisar Serviços*

🔜 *Funcionalidade em desenvolvimento!*

📝 *Use os botões abaixo para navegar.*
    """
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🛍️ *Histórico de Compras*

📊 *Em desenvolvimento...*
    """
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# ========== INICIALIZAR BOT ==========
def main():
    # Configurar logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Criar aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    
    # Callback handlers
    callbacks = [
        ("back_to_main", start),
        ("premium_products", premium_products),
        ("product_", view_product),
        ("buy_", buy_product),
        ("recharge", recharge_menu),
        ("profile", user_profile),
        ("info", bot_info),
        ("ranking", show_ranking),
        ("search", handle_search),
        ("history", show_history),
    ]
    
    for pattern, handler in callbacks:
        if pattern.endswith('_'):
            application.add_handler(CallbackQueryHandler(handler, pattern=f"^{pattern}"))
        else:
            application.add_handler(CallbackQueryHandler(handler, pattern=f"^{pattern}$"))
    
    # Iniciar bot
    print("🤖 BOT JOÃO STORE INICIADO!")
    print(f"🔗 https://t.me/{BOT_USERNAME.replace('@', '')}")
    application.run_polling()

if __name__ == '__main__':
    main()
