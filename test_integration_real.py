#!/usr/bin/env python3
"""
Teste de integração real usando streamlit.testing.v1.AppTest
Valida o fluxo completo: login -> destino -> ideia -> rascunhar -> auditoria -> síntese
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from streamlit.testing.v1 import AppTest


def test_full_flow():
    """Testa fluxo completo do cockpit"""
    at = AppTest.from_file("app.py").run()
    
    # Simulate login
    at.session_state["autenticado"] = True
    at.session_state["user_email"] = "test@example.com"
    at = at.run()
    
    # Select destination
    dest_sb = at.get("selectbox")[0]
    dest_sb.select("Flux.1 / Flux.2 (Klein)")
    at = at.run()
    
    assert at.session_state.get("ck_destino_select") == "Flux.1 / Flux.2 (Klein)"
    assert at.session_state.get("ck_destino_aplicado") == "Flux.1 / Flux.2 (Klein)"
    print("✅ Destino selecionado corretamente")
    
    # The text_area widget value comes from session_state key
    # In AppTest, we need to set the session_state key directly
    test_ideia = "Mulher jovem, cabelo ruivo, olhos verdes, vestido vermelho, biblioteca antiga, luz de vela, 85mm f/1.8"
    at.session_state["ck_ideia_input"] = test_ideia
    at = at.run()
    
    assert at.session_state.get("ck_ideia_input") == test_ideia
    print("✅ Ideia definida no session_state")
    
    # Click Rascunhar Cena
    btn_rascunhar = at.get("button")[2]  # "👁️ Rascunhar Cena"
    btn_rascunhar.click()
    at = at.run(timeout=30)
    
    # Check that PREPROMPT was generated
    preprompt = at.session_state.get("ck_preprompt", "")
    assert preprompt != "", f"PREPROMPT vazio! session_state keys: {[k for k in at.session_state.keys() if 'pre' in k.lower()]}"
    print(f"✅ Rascunhar Cena gerou PREPROMPT ({len(preprompt)} chars)")
    
    # Check PREPROMPT_EDITADO also populated
    pre_editado = at.session_state.get("ck_preprompt_editado", "")
    assert pre_editado != "", "PREPROMPT_EDITADO vazio"
    print(f"✅ PREPROMPT_EDITADO populado ({len(pre_editado)} chars)")
    
    # Click Auditoria
    btn_auditoria = at.get("button")[3]  # "🔍 Auditar no Compositômetro"
    btn_auditoria.click()
    at = at.run(timeout=30)
    
    diagnostico = at.session_state.get("ck_diagnostico")
    assert diagnostico is not None, "Diagnóstico não gerado"
    print(f"✅ Auditoria gerou diagnóstico: {diagnostico}")
    
    # Click Gerar Código do Prompt (Síntese final)
    btn_sintese = at.get("button")[4]  # "⚡ Gerar Código do Prompt"
    btn_sintese.click()
    at = at.run(timeout=30)
    
    prompt_final = at.session_state.get("ck_prompt_final", "")
    assert prompt_final != "", "Prompt final não gerado"
    print(f"✅ Síntese final gerou prompt ({len(prompt_final)} chars)")
    
    # Verify model defaults are correct (not gemini-1.5-flash)
    modelo_visao = at.session_state.get("modelo_visao_select")
    modelo_texto = at.session_state.get("modelo_texto_select")
    assert modelo_visao in ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"], f"Modelo visão inválido: {modelo_visao}"
    assert modelo_texto in ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"], f"Modelo texto inválido: {modelo_texto}"
    assert modelo_visao != "gemini-1.5-flash", "Modelo visão ainda usa default antigo"
    assert modelo_texto != "gemini-1.5-flash", "Modelo texto ainda usa default antigo"
    print(f"✅ Modelos corretos: visão={modelo_visao}, texto={modelo_texto}")
    
    # No exceptions
    assert len(at.exception) == 0, f"Exceções encontradas: {at.exception}"
    print("✅ Nenhuma exceção durante o fluxo")
    
    return True


def test_vision_model_default():
    """Testa que o modelo de visão usa MODELO_VISAO_PADRAO como default"""
    at = AppTest.from_file("app.py").run()
    
    at.session_state["autenticado"] = True
    at.session_state["user_email"] = "test@example.com"
    at = at.run()
    
    # Check vision model selectbox default
    vision_sb = at.get("selectbox")[3]  # Modelo Visão
    assert vision_sb.value == "gemini-3.5-flash", f"Default visão errado: {vision_sb.value}"
    print(f"✅ Modelo visão default: {vision_sb.value}")
    
    # Check text model selectbox default
    texto_sb = at.get("selectbox")[4]  # Modelo Texto
    assert texto_sb.value == "gemini-3.5-flash", f"Default texto errado: {texto_sb.value}"
    print(f"✅ Modelo texto default: {texto_sb.value}")


def test_idea_persistence_across_steps():
    """Testa que a ideia persiste entre passos (não some ao clicar botões)"""
    at = AppTest.from_file("app.py").run()
    
    at.session_state["autenticado"] = True
    at.session_state["user_email"] = "test@example.com"
    at.session_state["ck_destino_select"] = "Flux.1 / Flux.2 (Klein)"
    at.session_state["ck_destino_aplicado"] = "Flux.1 / Flux.2 (Klein)"
    at.session_state["ck_ideia_input"] = "Ideia de teste para persistência"
    at.session_state["modelo_visao_select"] = "gemini-3.5-flash"
    at.session_state["modelo_texto_select"] = "gemini-3.5-flash"
    at = at.run()
    
    original_ideia = at.session_state.get("ck_ideia_input")
    assert original_ideia == "Ideia de teste para persistência"
    
    # Click Rascunhar Cena
    btn_rascunhar = at.get("button")[2]
    btn_rascunhar.click()
    at = at.run(timeout=30)
    
    # Idea should still be there
    after_ideia = at.session_state.get("ck_ideia_input")
    assert after_ideia == original_ideia, f"Ideia mudou! Antes: '{original_ideia}', Depois: '{after_ideia}'"
    print(f"✅ Ideia persistiu após Rascunhar Cena: '{after_ideia[:40]}...'")
    
    # Click Auditoria
    btn_auditoria = at.get("button")[3]
    btn_auditoria.click()
    at = at.run(timeout=30)
    
    after_ideia2 = at.session_state.get("ck_ideia_input")
    assert after_ideia2 == original_ideia, f"Ideia mudou após Auditoria! '{after_ideia2}'"
    print("✅ Ideia persistiu após Auditoria")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE INTEGRAÇÃO REAL - PROMPT STUDIO COCKPIT")
    print("=" * 60)
    
    try:
        print("\n1. Testando modelo defaults...")
        test_vision_model_default()
        
        print("\n2. Testando persistência de ideia...")
        test_idea_persistence_across_steps()
        
        print("\n3. Testando fluxo completo...")
        test_full_flow()
        
        print("\n" + "=" * 60)
        print("✅ TODOS OS TESTES DE INTEGRAÇÃO PASSARAM")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ FALHA: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)