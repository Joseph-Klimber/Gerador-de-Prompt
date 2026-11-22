// ============================================================
// Apps Script - Code.gs (Backend de Produção: Licenças + Configs)
// ============================================================
// DEPLOY:
// 1. script.google.com → Novo projeto → Cole este código
// 2. Substitua YOUR_SHEET_ID pelo ID da sua planilha Google Sheets
// 3. Propriedades do script (⚙️ → Propriedades do script):
//    HMAC_KEY = <mesma PS_FERNET_KEY do secrets.toml do Streamlit>
//    SHEET_ID = <id da planilha>  (opcional, sobrescreve constante abaixo)
// 4. Deploy → Nova implantação → Tipo: App da Web
//    - Executar como: Eu
//    - Quem tem acesso: Qualquer pessoa
// 5. Cole a URL gerada no secrets.toml como APPS_SCRIPT_URL
// ============================================================

const SHEET_ID = "YOUR_SHEET_ID"; // SUBSTITUA PELO ID DA SUA PLANILHA (ou defina em Propriedades do script)
const SHEET_NAME = "Assinaturas"; // Aba com colunas: Email | Expiracao | Config (JSON string)
const MAX_REQUESTS_PER_MINUTE_EMAIL = 20;
const MAX_REQUESTS_PER_MINUTE_IP = 60;
const CACHE_TTL = 60; // segundos

function doPost(e) {
  const startTime = Date.now();
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    return jsonResponse({ok: false, erro: "Servidor ocupado, tente novamente"}, startTime, "lock_timeout");
  }

  try {
    const ip = getClientIdentifier(e);
    const data = JSON.parse(e.postData.contents);
    const action = (data.action || "").toLowerCase();
    const email = (data.email || "").toLowerCase().trim();

    // Log estruturado de entrada
    logStructured({ts: isoNow(), email, action, ip, phase: "request_received"});

    if (!email || !email.includes("@")) {
      return jsonResponse({ok: false, erro: "Não autorizado"}, startTime, "invalid_email", email, action);
    }

    // HMAC verification on config actions (salvar/carregar)
    if (action === "salvar" || action === "carregar") {
      const signature = e.headers["X-Signature"] || e.headers["x-signature"] || "";
      const payloadStr = e.postData.contents;
      if (!verifyHmac(payloadStr, signature)) {
        logStructured({ts: isoNow(), email, action, ip, ok: false, latencyMs: Date.now() - startTime, error: "HMAC verification failed"});
        return jsonResponse({ok: false, erro: "Assinatura inválida"}, startTime, "hmac_fail", email, action);
      }
    }

    // Rate limit: dual key (email + IP)
    if (!checkRateLimitDual(email, ip)) {
      logStructured({ts: isoNow(), email, action, ip, ok: false, latencyMs: Date.now() - startTime, error: "Rate limit exceeded"});
      return jsonResponse({ok: false, erro: "Muitas tentativas. Aguarde 1 minuto."}, startTime, "rate_limit", email, action);
    }

    const sheetId = PropertiesService.getScriptProperties().getProperty("SHEET_ID") || SHEET_ID;
    if (!sheetId || sheetId === "YOUR_SHEET_ID") {
      logStructured({ts: isoNow(), email, action, ip, ok: false, latencyMs: Date.now() - startTime, error: "SHEET_ID not configured"});
      return jsonResponse({ok: false, erro: "Servidor não configurado (SHEET_ID)"}, startTime, "config_error", email, action);
    }
    const sheet = SpreadsheetApp.openById(sheetId).getSheetByName(SHEET_NAME);
    if (!sheet) {
      logStructured({ts: isoNow(), email, action, ip, ok: false, latencyMs: Date.now() - startTime, error: "Sheet not found"});
      return jsonResponse({ok: false, erro: "Aba não encontrada"}, startTime, "sheet_error", email, action);
    }

    let response;
    switch (action) {
      case "verificar":
        response = handleVerificar(sheet, email);
        break;
      case "carregar":
        response = handleCarregar(sheet, email);
        break;
      case "salvar":
        const payload = data.payload; // Fernet token (ciphertext)
        if (!payload) {
          response = {ok: false, erro: "Payload não fornecido"};
        } else {
          response = handleSalvar(sheet, email, payload);
        }
        break;
      default:
        response = {ok: false, erro: "Ação inválida"};
    }

    // Sign response for carregar (includes payload)
    if (action === "carregar" && response.ok && response.payload) {
      const responseCopy = {ok: true, payload: response.payload};
      response.hmac = signHmac(canonicalJson(responseCopy));
    }

    logStructured({
      ts: isoNow(),
      email,
      action,
      ip,
      ok: response.ok === true,
      latencyMs: Date.now() - startTime,
      error: response.ok ? "" : (response.erro || "unknown")
    });

    return jsonResponse(response, startTime, undefined, email, action);

  } catch (err) {
    logStructured({ts: isoNow(), email: email || "unknown", action: action || "unknown", ip: ip || "unknown", ok: false, latencyMs: Date.now() - startTime, error: err.toString()});
    return jsonResponse({ok: false, erro: "Erro interno"}, startTime, "exception", email || "", action || "");
  } finally {
    lock.releaseLock();
  }
}

function handleVerificar(sheet, email) {
  const rows = sheet.getDataRange().getValues();
  let authorized = false;
  let expiracao = "";

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

  return {
    ok: authorized,
    expiracao: authorized ? expiracao : "",
    erro: authorized ? "" : "Não autorizado"
  };
}

function handleCarregar(sheet, email) {
  const rows = sheet.getDataRange().getValues();

  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] && rows[i][0].toString().toLowerCase() === email) {
      const payload = rows[i][2]; // stored Fernet token (ciphertext)
      if (payload) {
        return {ok: true, payload: payload};
      }
      return {ok: false, erro: "Não autorizado"};
    }
  }
  return {ok: false, erro: "Não autorizado"};
}

function handleSalvar(sheet, email, payload) {
  const rows = sheet.getDataRange().getValues();
  let rowIndex = -1;

  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] && rows[i][0].toString().toLowerCase() === email) {
      rowIndex = i + 1;
      break;
    }
  }

  if (rowIndex > 0) {
    sheet.getRange(rowIndex, 3).setValue(payload);
  } else {
    sheet.appendRow([email, new Date(), payload]);
  }

  return {ok: true};
}

function jsonResponse(obj, startTime, errorCode, email, action) {
  const out = ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
  // No log here (already logged in doPost); just return
  return out;
}

function getClientIdentifier(e) {
  // Prefer X-Forwarded-For (if behind proxy), fallback to e.parameters or headers
  const headers = e.headers || {};
  let ip = headers["X-Forwarded-For"] || headers["x-forwarded-for"] || headers["X-Real-IP"] || headers["x-real-ip"] || "";
  if (ip) {
    // X-Forwarded-For can be a list; take first
    ip = ip.split(",")[0].trim();
  }
  if (!ip) {
    // Apps Script doesn't expose client IP directly; use UA hash as fallback
    const ua = headers["User-Agent"] || "unknown";
    ip = "ua:" + Utilities.getUuid().substring(0, 8);
  }
  return ip;
}

function checkRateLimitDual(email, ip) {
  const cache = CacheService.getScriptCache();
  const emailKey = "rate:email:" + email;
  const ipKey = "rate:ip:" + ip;

  const emailCount = parseInt(cache.get(emailKey) || "0");
  const ipCount = parseInt(cache.get(ipKey) || "0");

  if (emailCount >= MAX_REQUESTS_PER_MINUTE_EMAIL) return false;
  if (ipCount >= MAX_REQUESTS_PER_MINUTE_IP) return false;

  cache.put(emailKey, (emailCount + 1).toString(), CACHE_TTL);
  cache.put(ipKey, (ipCount + 1).toString(), CACHE_TTL);
  return true;
}

// --- HMAC (SHA256) ---
// Key derivation: HMAC_KEY property = PS_FERNET_KEY (44-char url-safe base64 string).
// Both sides use raw string bytes as HMAC key (no base64Decode, no SHA256 derivation).
// This ensures deterministic match: Python hmac.new(key.encode(), ...) == Apps Script computeHmacSha256Signature(..., keyStr).

function hmacKeyString() {
  return PropertiesService.getScriptProperties().getProperty("HMAC_KEY") || "";
}

function signHmac(payload) {
  const key = hmacKeyString();
  if (!key) return "";
  // payload: String, key: String → returns Byte[]
  const sigBytes = Utilities.computeHmacSha256Signature(payload, key);
  // base64url encode (no padding)
  return Utilities.base64EncodeWebSafe(sigBytes).replace(/=/g, "");
}

function verifyHmac(payload, signatureB64url) {
  if (!signatureB64url) return false;
  const expected = signHmac(payload);
  return constantTimeCompare(expected, signatureB64url);
}

function constantTimeCompare(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

// Canonical JSON for signing (sorted keys, no spaces, ensure_ascii=false equivalent)
function canonicalJson(obj) {
  if (obj === null || typeof obj !== "object") {
    if (typeof obj === "string") return '"' + obj.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
    return String(obj);
  }
  if (Array.isArray(obj)) {
    return "[" + obj.map(canonicalJson).join(",") + "]";
  }
  const keys = Object.keys(obj).sort();
  return "{" + keys.map(k => '"' + k + '":' + canonicalJson(obj[k])).join(",") + "}";
}

function isoNow() {
  return new Date().toISOString();
}

function logStructured(entry) {
  // console.info goes to Cloud Logging when deployed as Web App
  console.info(JSON.stringify(entry));
}