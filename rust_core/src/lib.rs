use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::collections::HashMap;

// ── Password Hashing ─────────────────────────────────────────────────────────

/// Hash a password using Argon2id (memory-hard, GPU-resistant).
#[pyfunction]
fn hash_password(password: &str) -> PyResult<String> {
    use argon2::{
        password_hash::{rand_core::OsRng, PasswordHasher, SaltString},
        Argon2,
    };
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();
    argon2
        .hash_password(password.as_bytes(), &salt)
        .map(|h| h.to_string())
        .map_err(|e| PyValueError::new_err(format!("Hash error: {}", e)))
}

/// Verify a password against a hash.
/// Supports BOTH Argon2id (new) and bcrypt (legacy) hashes for migration.
#[pyfunction]
fn verify_password(password: &str, hash: &str) -> PyResult<bool> {
    if hash.starts_with("$2b$") || hash.starts_with("$2a$") || hash.starts_with("$2y$") {
        // Legacy bcrypt hash — verify with bcrypt
        Ok(bcrypt::verify(password, hash).unwrap_or(false))
    } else if hash.starts_with("$argon2") {
        // Argon2id hash
        use argon2::{
            password_hash::{PasswordHash, PasswordVerifier},
            Argon2,
        };
        let parsed = PasswordHash::new(hash)
            .map_err(|e| PyValueError::new_err(format!("Invalid hash: {}", e)))?;
        Ok(Argon2::default()
            .verify_password(password.as_bytes(), &parsed)
            .is_ok())
    } else {
        Err(PyValueError::new_err("Unknown hash format"))
    }
}

/// Check if a hash is bcrypt (needs migration to Argon2id).
#[pyfunction]
fn is_legacy_hash(hash: &str) -> bool {
    hash.starts_with("$2b$") || hash.starts_with("$2a$") || hash.starts_with("$2y$")
}

// ── JWT ──────────────────────────────────────────────────────────────────────

use jsonwebtoken::{encode, decode, Header, Validation, EncodingKey, DecodingKey, Algorithm};
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    email: Option<String>,
    role: Option<String>,
    exp: usize,
}

/// Create a JWT token with HS256.
#[pyfunction]
fn create_jwt(payload: HashMap<String, String>, secret: &str, ttl_minutes: u64) -> PyResult<String> {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| PyValueError::new_err(format!("Time error: {}", e)))?;
    let exp = now.as_secs() + (ttl_minutes * 60);

    let claims = Claims {
        sub: payload.get("sub").cloned().unwrap_or_default(),
        email: payload.get("email").cloned(),
        role: payload.get("role").cloned(),
        exp: exp as usize,
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )
    .map_err(|e| PyValueError::new_err(format!("JWT encode error: {}", e)))
}

/// Decode and validate a JWT token. Returns None (as empty dict) if invalid.
#[pyfunction]
fn decode_jwt(token: &str, secret: &str) -> PyResult<Option<HashMap<String, String>>> {
    let validation = Validation::new(Algorithm::HS256);
    match decode::<Claims>(token, &DecodingKey::from_secret(secret.as_bytes()), &validation) {
        Ok(data) => {
            let mut map = HashMap::new();
            map.insert("sub".to_string(), data.claims.sub);
            if let Some(email) = data.claims.email {
                map.insert("email".to_string(), email);
            }
            if let Some(role) = data.claims.role {
                map.insert("role".to_string(), role);
            }
            map.insert("exp".to_string(), data.claims.exp.to_string());
            Ok(Some(map))
        }
        Err(_) => Ok(None),
    }
}

// ── Input Validation / Sanitization ──────────────────────────────────────────

/// Sanitize HTML input — removes dangerous tags/attributes, keeps safe text.
#[pyfunction]
fn sanitize_html(input: &str) -> String {
    ammonia::clean(input)
}

/// Strip ALL HTML tags — return plain text only.
#[pyfunction]
fn strip_tags(input: &str) -> String {
    ammonia::Builder::new()
        .tags(std::collections::HashSet::new())
        .clean(input)
        .to_string()
}

/// Validate an Argentine CUIT/CUIL format (XX-XXXXXXXX-X).
#[pyfunction]
fn validate_cuit(cuit: &str) -> bool {
    let digits: String = cuit.chars().filter(|c| c.is_ascii_digit()).collect();
    if digits.len() != 11 {
        return false;
    }
    // Verify check digit
    let weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
    let sum: u32 = digits[..10]
        .chars()
        .zip(weights.iter())
        .map(|(c, &w)| c.to_digit(10).unwrap_or(0) * w)
        .sum();
    let remainder = sum % 11;
    let check = if remainder == 0 { 0 } else if remainder == 1 { 9 } else { 11 - remainder };
    let last = digits.chars().last().and_then(|c| c.to_digit(10)).unwrap_or(99);
    check == last
}

/// Validate an email address format.
#[pyfunction]
fn validate_email(email: &str) -> bool {
    let re = regex::Regex::new(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    ).unwrap();
    re.is_match(email) && email.contains('.')
}

// ── AES-256-GCM Encryption ──────────────────────────────────────────────────

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};
use rand::RngCore;

/// Encrypt a string with AES-256-GCM. Key must be exactly 32 bytes (use SHA256 of passphrase).
/// Returns base64-encoded nonce+ciphertext.
#[pyfunction]
fn encrypt_sensitive(data: &str, key_hex: &str) -> PyResult<String> {
    let key_bytes = hex_decode(key_hex)
        .map_err(|e| PyValueError::new_err(format!("Invalid key hex: {}", e)))?;
    if key_bytes.len() != 32 {
        return Err(PyValueError::new_err("Key must be 32 bytes (64 hex chars)"));
    }

    let cipher = Aes256Gcm::new_from_slice(&key_bytes)
        .map_err(|e| PyValueError::new_err(format!("Cipher error: {}", e)))?;

    let mut nonce_bytes = [0u8; 12];
    rand::thread_rng().fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ciphertext = cipher
        .encrypt(nonce, data.as_bytes())
        .map_err(|e| PyValueError::new_err(format!("Encryption error: {}", e)))?;

    // Prepend nonce to ciphertext and base64 encode
    let mut combined = nonce_bytes.to_vec();
    combined.extend_from_slice(&ciphertext);
    Ok(BASE64.encode(&combined))
}

/// Decrypt a string encrypted with encrypt_sensitive.
#[pyfunction]
fn decrypt_sensitive(encrypted_b64: &str, key_hex: &str) -> PyResult<String> {
    let key_bytes = hex_decode(key_hex)
        .map_err(|e| PyValueError::new_err(format!("Invalid key hex: {}", e)))?;
    if key_bytes.len() != 32 {
        return Err(PyValueError::new_err("Key must be 32 bytes (64 hex chars)"));
    }

    let combined = BASE64.decode(encrypted_b64)
        .map_err(|e| PyValueError::new_err(format!("Base64 decode error: {}", e)))?;

    if combined.len() < 13 {
        return Err(PyValueError::new_err("Invalid ciphertext"));
    }

    let (nonce_bytes, ciphertext) = combined.split_at(12);
    let cipher = Aes256Gcm::new_from_slice(&key_bytes)
        .map_err(|e| PyValueError::new_err(format!("Cipher error: {}", e)))?;
    let nonce = Nonce::from_slice(nonce_bytes);

    let plaintext = cipher
        .decrypt(nonce, ciphertext)
        .map_err(|_| PyValueError::new_err("Decryption failed — invalid key or corrupted data"))?;

    String::from_utf8(plaintext)
        .map_err(|e| PyValueError::new_err(format!("UTF-8 error: {}", e)))
}

fn hex_decode(hex: &str) -> Result<Vec<u8>, String> {
    if hex.len() % 2 != 0 {
        return Err("Odd-length hex string".to_string());
    }
    (0..hex.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).map_err(|e| e.to_string()))
        .collect()
}

// ── Python Module ────────────────────────────────────────────────────────────

#[pymodule]
fn rust_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(verify_password, m)?)?;
    m.add_function(wrap_pyfunction!(is_legacy_hash, m)?)?;
    m.add_function(wrap_pyfunction!(create_jwt, m)?)?;
    m.add_function(wrap_pyfunction!(decode_jwt, m)?)?;
    m.add_function(wrap_pyfunction!(sanitize_html, m)?)?;
    m.add_function(wrap_pyfunction!(strip_tags, m)?)?;
    m.add_function(wrap_pyfunction!(validate_cuit, m)?)?;
    m.add_function(wrap_pyfunction!(validate_email, m)?)?;
    m.add_function(wrap_pyfunction!(encrypt_sensitive, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt_sensitive, m)?)?;
    Ok(())
}
