import React, { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';

function AdminPaymentsPage() {
  const [settings, setSettings] = useState({
    crystalpay_api_key: '',
    crystalpay_api_secret: '',
    heleket_api_key: '',
    platega_merchant_id: '',
    platega_secret: '',
    telegram_bot_token: ''
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null); // 'saving', 'success', 'error'
  const { token } = useAuth();
  
  // --- 1. Загрузка текущих ключей ---
  useEffect(() => {
    const fetchSettings = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/admin/payment-settings', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Не удалось загрузить настройки');
        const data = await response.json();
        // ❗️ API вернет "DECRYPTION_ERROR" если ключи пустые,
        // ❗️ мы заменим это на пустую строку для формы
        if (data.crystalpay_api_key === "DECRYPTION_ERROR") data.crystalpay_api_key = "";
        if (data.crystalpay_api_secret === "DECRYPTION_ERROR") data.crystalpay_api_secret = "";
        if (data.heleket_api_key === "DECRYPTION_ERROR") data.heleket_api_key = "";
        if (data.platega_merchant_id === "DECRYPTION_ERROR") data.platega_merchant_id = "";
        if (data.platega_secret === "DECRYPTION_ERROR") data.platega_secret = "";
        if (data.telegram_bot_token === "DECRYPTION_ERROR") data.telegram_bot_token = "";
        setSettings(data);
      } catch (e) { 
        setError(e.message); 
      } finally { 
        setLoading(false); 
      }
    };
    
    if (token) {
      fetchSettings();
    }
  }, [token]);

  // --- 2. Обработчик изменения полей ---
  const handleChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // --- 3. Сохранение настроек ---
  const handleSave = async (e) => {
    e.preventDefault();
    setSaveStatus('saving');
    setError(null);
    try {
      const response = await fetch('/api/admin/payment-settings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Ошибка сохранения');
      
      setSaveStatus('success');
      setTimeout(() => setSaveStatus(null), 2000); // Показать "Сохранено!" на 2 сек

    } catch (e) {
      setError(e.message);
      setSaveStatus('error');
    }
  };
  
  if (loading) {
    return (
      <main className="admin-page-content">
        <section><div className="loading-mini">Загрузка...</div></section>
      </main>
    );
  }

  return (
    <main className="admin-page-content">
      <section>
        <h2>Настройки Платежных Систем</h2>
        <p className="admin-description-text">
          Ключи API шифруются на сервере и никогда не хранятся в открытом виде.
        </p>
        
        {error && <div className="message-error">{error}</div>}
        
        <form className="tariff-form" onSubmit={handleSave}>
          
          {/* --- CrystalPAY --- */}
          <h3>CrystalPAY</h3>
          <div className="form-row">
            <div className="form-group">
              <label>API Key (Cassa ID)</label>
              <input 
                type="text" 
                name="crystalpay_api_key"
                value={settings.crystalpay_api_key} 
                onChange={handleChange} 
                placeholder="Например, mykassa"
              />
            </div>
            <div className="form-group">
              <label>API Secret (Secret Key 1)</label>
              <input 
                type="text" 
                name="crystalpay_api_secret"
                value={settings.crystalpay_api_secret} 
                onChange={handleChange} 
                placeholder="Секретный ключ..."
              />
            </div>
          </div>
          
          {/* --- Heleket --- */}
          <h3 style={{marginTop: '30px'}}>Heleket</h3>
          <div className="form-row">
            <div className="form-group">
              <label>API Key</label>
              <input 
                type="text" 
                name="heleket_api_key"
                value={settings.heleket_api_key} 
                onChange={handleChange} 
                placeholder="API ключ Heleket..."
              />
            </div>
          </div>
          
          {/* --- Platega --- */}
          <h3 style={{marginTop: '30px'}}>Platega</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Merchant ID (X-MerchantId)</label>
              <input 
                type="text" 
                name="platega_merchant_id"
                value={settings.platega_merchant_id} 
                onChange={handleChange} 
                placeholder="UUID из Platega"
              />
            </div>
            <div className="form-group">
              <label>Secret (X-Secret)</label>
              <input 
                type="text" 
                name="platega_secret"
                value={settings.platega_secret} 
                onChange={handleChange} 
                placeholder="Секрет Platega"
              />
            </div>
          </div>
          
          {/* --- Telegram Stars --- */}
          <h3 style={{marginTop: '30px'}}>Telegram Stars ⭐</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Bot Token</label>
              <input 
                type="text" 
                name="telegram_bot_token"
                value={settings.telegram_bot_token} 
                onChange={handleChange} 
                placeholder="Bot Token от @BotFather..."
              />
            </div>
          </div>
          
          {/* --- YooKassa (На будущее) --- */}
          <h3 style={{marginTop: '30px'}}>YooKassa (в разработке)</h3>
          <div className="form-row">
            <div className="form-group">
              <label>Shop ID</label>
              <input type="text" disabled placeholder="Недоступно"/>
            </div>
            <div className="form-group">
              <label>Secret Key</label>
              <input type="text" disabled placeholder="Недоступно"/>
            </div>
          </div>
          
          {/* --- Кнопка сохранения --- */}
          <div style={{display: 'flex', alignItems: 'center', gap: '20px', marginTop: '20px'}}>
            <button 
              type="submit" 
              className="btn" 
              style={{maxWidth: '200px'}}
              disabled={saveStatus === 'saving'}
            >
              {saveStatus === 'saving' ? 'Сохранение...' : 'Сохранить ключи'}
            </button>
            {saveStatus === 'success' && (
              <div className="message-success">Сохранено!</div>
            )}
          </div>
        </form>
      </section>
    </main>
  );
}

export default AdminPaymentsPage;
