// ============================================================
// Apps Script - Code.gs (Backend de Licenca + Configs + HMAC)
// ============================================================
// COLE ESTE CODIGO NO SEU PROJETO APPS SCRIPT (script.google.com)
// Substitua YOUR_SHEET_ID pelo ID da sua planilha Google Sheets
// Substitua YOUR_HMAC_KEY pela PS_FERNET_KEY (base64 32 bytes)
// Deploy -> New deployment -> Type: Web app -> Execute as: Me -> Who has access: Anyone
// Cole a URL gerada no Secrets do Streamlit Cloud como APPS_SCRIPT_URL
// ============================================================

const SHEET_ID = "180xWEBt4Lu8dqHQCBIwfyMgYA1vdN8eD1FehK-aiXLI"; // ID da planilha de produção
const SHEET_NAME = "Assinaturas"; // Aba com colunas: Email | Expiracao | Config (JSON string)
const HMAC_KEY = "YOUR_HMAC_KEY"; // SUBSTITUA PELA PS_FERNET_KEY (mesma chave do Streamlit)
const MAX_REQUESTS_PER_MINUTE_EMAIL = 20;
const MAX_REQUESTS_PER_MINUTE_IP = 60;
const CACHE_TTL = 60; // segundos

function doPost(e) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) {
    return jsonResponse({ok: false, erro: "Servidor ocupado, tente novamente"}, 429);
  }

  const startTime = new Date();

  try {
    const ip = getClientIdentifier(e);
    const email = (e.parameter.email || "").toLowerCase().trim();

    // Rate limit: email + IP (ambos devem passar)
    if (!checkRateLimit("email:" + email) || !checkRateLimit("ip:" + ip)) {
      return jsonResponse({ok: false, erro: "Muitas tentativas. Aguarde 1 minuto."}, 429);
    }

    // Verifica HMAC na requisição
    const payloadStr = e.postData.contents;
    const signature = e.headers["X-Signature"] || "";
    if (!verifyHmac(payloadStr, signature)) {
      logRequest(startTime, email, "hmac_fail", false, "HMAC inválido");
      return jsonResponse({ok: false, erro: "Assinatura inválida"}, 401);
    }

    const data = JSON.parse(payloadStr);
    const action = (data.action || "").toLowerCase();

    if (!email || !email.includes("@")) {
      logRequest(startTime, email, action, false, "E-mail inválido");
      return jsonResponse({ok: false, erro: "Não autorizado"}, 401);
    }

    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);

    let result;
    switch (action) {
      case "verificar":
        result = handleVerificar(sheet, email);
        break;
      case "carregar":
        result = handleCarregar(sheet, email);
        break;
      case "salvar":
        const config = data.config || data.payload; // compat: payload criptografado ou config
        if (!config) {
          result = jsonResponse({ok: false, erro: "Config não fornecida"});
          break;
        }
        result = handleSalvar(sheet, email, config);
        break;
      default:
        result = jsonResponse({ok: false, erro: "Ação inválida"});
    }

    // Adiciona HMAC na resposta
    const responseObj = JSON.parse(result.getContentText());
    const responseStr = JSON.stringify(responseObj, (k, v) => v === undefined ? null : v);
    const hmacSig = signHmac(responseStr);
    responseObj.hmac = hmacSig;

    logRequest(startTime, email, action, responseObj.ok, responseObj.erro || "");
    return ContentService.createTextOutput(JSON.stringify(responseObj))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    console.error("Apps Script Error:", err);
    logRequest(startTime, email || "unknown", "exception", false, err.toString());
    return jsonResponse({ok: false, erro: "Erro interno"}, 500);
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
      const configStr = rows[i][2];
      if (configStr) {
        try {
          const config = JSON.parse(configStr);
          return {ok: true, config: config};
        } catch (e) {
          return {ok: false, erro: "Config corrompida"};
        }
      }
      return {ok: false, erro: "Não autorizado"};
    }
  }
  return {ok: false, erro: "Não autorizado"};
}

function handleSalvar(sheet, email, config) {
  const rows = sheet.getDataRange().getValues();
  const configStr = typeof config === "string" ? config : JSON.stringify(config);
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

  return {ok: true};
}

function jsonResponse(obj, statusCode = 200) {
  const output = ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
  // Apps Script não permite set status code diretamente no Web App
  // Retornamos o objeto com erro - o cliente verifica obj.ok
  return output;
}

function getClientIdentifier(e) {
  const ua = e.headers["User-Agent"] || "unknown";
  // Usa IP do cabeçalho X-Forwarded-For se disponível (proxy), senão UUID
  const forwarded = e.headers["X-Forwarded-For"];
  if (forwarded) {
    return forwarded.split(",")[0].trim();
  }
  return Utilities.getUuid() + "-" + ua.substring(0, 20);
}

function checkRateLimit(key) {
  const cache = CacheService.getScriptCache();
  const fullKey = "ratelimit:" + key;
  const count = parseInt(cache.get(fullKey) || "0");
  const limit = key.startsWith("email:") ? MAX_REQUESTS_PER_MINUTE_EMAIL : MAX_REQUESTS_PER_MINUTE_IP;
  if (count >= limit) return false;
  cache.put(fullKey, (count + 1).toString(), CACHE_TTL);
  return true;
}

// ============================================================
// HMAC Helpers
// ============================================================

function signHmac(payload) {
  const keyBytes = Utilities.base64Decode(HMAC_KEY);
  const hmacKey = Utilities.computeHmacSha256Signature(payload, keyBytes);
  return Utilities.base64EncodeWebSafe(hmacKey).replace(/=/g, "");
}

function verifyHmac(payload, signature) {
  if (!signature) return false;
  const expected = signHmac(payload);
  // Constant-time comparison
  return compareDigest(expected, signature);
}

function compareDigest(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

// ============================================================
// Structured Logging
// ============================================================

function logRequest(startTime, email, action, ok, errorMsg) {
  const latencyMs = new Date() - startTime;
  const logEntry = {
    ts: new Date().toISOString(),
    email: email,
    action: action,
    ok: ok,
    latencyMs: latencyMs,
    error: errorMsg || null
  };
  console.info(JSON.stringify(logEntry));
}