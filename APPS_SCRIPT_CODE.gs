// ============================================================
// Apps Script - Code.gs (Backend de Licenca + Configs)
// ============================================================
// COLE ESTE CODIGO NO SEU PROJETO APPS SCRIPT (script.google.com)
// Substitua YOUR_SHEET_ID pelo ID da sua planilha Google Sheets
// Deploy -> New deployment -> Type: Web app -> Execute as: Me -> Who has access: Anyone
// Cole a URL gerada no Secrets do Streamlit Cloud como APPS_SCRIPT_URL
// ============================================================

const SHEET_ID = "YOUR_SHEET_ID"; // SUBSTITUA PELO ID DA SUA PLANILHA
const SHEET_NAME = "Assinaturas"; // Aba com colunas: Email | Expiracao | Config (JSON string)
const MAX_REQUESTS_PER_MINUTE = 10;
const CACHE_TTL = 60; // segundos

function doPost(e) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    return jsonResponse({ok: false, erro: "Servidor ocupado, tente novamente"});
  }

  try {
    const ip = getClientIdentifier(e);
    if (!checkRateLimit(ip)) {
      return jsonResponse({ok: false, erro: "Muitas tentativas. Aguarde 1 minuto."});
    }

    const data = JSON.parse(e.postData.contents);
    const action = (data.action || "").toLowerCase();
    const email = (data.email || "").toLowerCase().trim();

    if (!email || !email.includes("@")) {
      return jsonResponse({ok: false, erro: "Nao autorizado"});
    }

    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);

    switch (action) {
      case "verificar":
        return handleVerificar(sheet, email);
      case "carregar":
        return handleCarregar(sheet, email);
      case "salvar":
        const config = data.config;
        if (!config) return jsonResponse({ok: false, erro: "Config nao fornecida"});
        return handleSalvar(sheet, email, config);
      default:
        return jsonResponse({ok: false, erro: "Acao invalida"});
    }

  } catch (err) {
    console.error("Apps Script Error:", err);
    return jsonResponse({ok: false, erro: "Erro interno"});
  } finally {
    lock.releaseLock();
  }
}

function handleVerificar(sheet, email) {
  const rows = sheet.getDataRange().getValues();
  let authorized = false, expiracao = "";

  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] && rows[i][0].toString().toLowerCase() === email) {
      const exp = new Date(rows[i][1]);
      if (exp > new Date()) {
        authorized = true;
        expiracao = rows[i][1];
      }
      break;
    }
  }

  return jsonResponse({
    ok: authorized,
    expiracao: authorized ? expiracao : "",
    erro: authorized ? "" : "Nao autorizado"
  });
}

function handleCarregar(sheet, email) {
  const rows = sheet.getDataRange().getValues();

  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] && rows[i][0].toString().toLowerCase() === email) {
      const configStr = rows[i][2];
      if (configStr) {
        try {
          const config = JSON.parse(configStr);
          return jsonResponse({ok: true, config: config});
        } catch (e) {
          return jsonResponse({ok: false, erro: "Config corrompida"});
        }
      }
      return jsonResponse({ok: false, erro: "Nao autorizado"});
    }
  }
  return jsonResponse({ok: false, erro: "Nao autorizado"});
}

function handleSalvar(sheet, email, config) {
  const rows = sheet.getDataRange().getValues();
  const configStr = JSON.stringify(config);
  let rowIndex = -1;

  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] && rows[i][0].toString().toLowerCase() === email) {
      rowIndex = i + 1;
      break;
    }
  }

  if (rowIndex > 0) {
    sheet.getRange(rowIndex, 3).setValue(configStr);
  } else {
    sheet.appendRow([email, new Date(), configStr]);
  }

  return jsonResponse({ok: true});
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function getClientIdentifier(e) {
  const ua = e.headers["User-Agent"] || "unknown";
  return Utilities.getUuid() + "-" + ua.substring(0, 20);
}

function checkRateLimit(key) {
  const cache = CacheService.getScriptCache();
  const count = parseInt(cache.get(key) || "0");
  if (count >= MAX_REQUESTS_PER_MINUTE) return false;
  cache.put(key, (count + 1).toString(), CACHE_TTL);
  return true;
}

// ============================================================
// OPCIONAL: CAPTCHA Turnstile (Cloudflare - Gratis Ilimitado)
// ============================================================
// 1. Crie site em https://dash.cloudflare.com/ -> Turnstile -> Add site
// 2. Pegue Site Key + Secret Key
// 3. No app.py (frontend), adicione widget Turnstile no login
// 4. No doPost acima, adicione:
//    if (data.captcha && !verifyTurnstile(data.captcha)) return jsonResponse({ok: false, erro: "CAPTCHA invalido"});
//
// function verifyTurnstile(token) {
//   const secret = "SUA_SECRET_KEY_TURNSTILE";
//   const payload = {secret: secret, response: token};
//   const options = {
//     method: "post",
//     payload: payload,
//     muteHttpExceptions: true
//   };
//   const resp = UrlFetchApp.fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", options);
//   return JSON.parse(resp.getContentText()).success === true;
// }
