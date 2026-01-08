import json
import os
import re
import glob
from time import sleep
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES E FUNÇÕES AUXILIARES (MANTENHA IGUAL AO ANTERIOR) ---
ARQUIVO_HISTORICO = "historico_downloads.json"
PASTA_DOWNLOAD = os.path.join(os.getcwd(), "dados_raw")
MAX_TENTATIVAS = 3 

if not os.path.exists(PASTA_DOWNLOAD):
    os.makedirs(PASTA_DOWNLOAD)

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, 'r') as f:
            return json.load(f)
    return {}

def salvar_historico(dados):
    with open(ARQUIVO_HISTORICO, 'w') as f:
        json.dump(dados, f, indent=4)

def limpar_nome_arquivo(nome):
    return re.sub(r'[\\/*?:"<>|]', "", nome)

def extrair_detalhes(texto_linha):
    match = re.search(r'^(\d+)\s*(.*?)\s*(\d{4}/\d{2})$', texto_linha.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    return None, None, None

def obter_arquivos_xlsx():
    return set(glob.glob(os.path.join(PASTA_DOWNLOAD, "*.xlsx")))

def fechar_popup_se_existir(driver):
    """
    Versão Turbo: Tenta fechar qualquer tipo de modal, alerta ou aviso.
    Retorna True se encontrou e fechou algo.
    """
    try:
        # Lista expandida de seletores para pegar qualquer variação de botão de fechar
        xpaths_botoes = [
            # Botões com texto explícito
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Ok')]",
            "//button[contains(text(), 'ok')]",
            "//button[contains(text(), 'Confirmar')]",
            "//button[contains(text(), 'Entendi')]",
            "//button[contains(text(), 'Fechar')]",
            "//button[contains(text(), 'Sim')]",
            
            # Links estilizados como botões (comum em Bootstrap/Metronic)
            "//a[contains(@class, 'btn') and contains(text(), 'OK')]",
            "//a[contains(@class, 'btn') and contains(text(), 'Confirmar')]",
            
            # Botões pelo ID ou Classe comuns
            "//*[@id='btnOk']",
            "//*[@id='btnConfirmar']",
            "//button[contains(@class, 'confirm')]", # SweetAlert
            "//button[contains(@class, 'swal-button')]", # SweetAlert moderno
            
            # Botão de fechar (X) no topo de modais
            "//button[@class='close']",
            "//button[@aria-label='Close']",
            "//div[@class='modal-header']//button",
            
            # Botão genérico no rodapé do modal (último recurso)
            "//div[contains(@class, 'modal-footer')]//button[1]" 
        ]

        for xpath in xpaths_botoes:
            # Procura elementos visíveis
            elementos = driver.find_elements(By.XPATH, xpath)
            for btn in elementos:
                if btn.is_displayed() and btn.is_enabled():
                    print(f" -> [POP-UP DETECTADO] Clicando em: {xpath}")
                    # Tenta clique JS (mais forte)
                    driver.execute_script("arguments[0].click();", btn)
                    sleep(2) # Espera o modal sumir
                    return True
        
        # Tenta fechar ALERT nativo do navegador (aquelas caixas cinzas do topo)
        try:
            alert = driver.switch_to.alert
            print(f" -> [ALERT NATIVO] Texto: {alert.text}")
            alert.accept()
            sleep(1)
            return True
        except:
            pass

    except Exception as e:
        print(f" -> Erro ao tentar fechar popup: {e}")
        pass
    
    return False

def esperar_novo_arquivo_e_renomear(arquivos_antes, nome_obra, competencia):
    print(" -> Aguardando novo arquivo...")
    tempo_limite = 60
    tempo_decorrido = 0
    
    while tempo_decorrido < tempo_limite:
        arquivos_agora = obter_arquivos_xlsx()
        novos_arquivos = arquivos_agora - arquivos_antes
        
        if novos_arquivos:
            arquivo_novo = list(novos_arquivos)[0]
            if not arquivo_novo.endswith('.crdownload'):
                try:
                    if os.path.getsize(arquivo_novo) > 0:
                        sleep(1) 
                        comp_arquivo = competencia.replace('/', '-')
                        novo_nome = f"Relatorio Folha de Pagamento - {nome_obra} - {comp_arquivo}.xlsx"
                        novo_nome = limpar_nome_arquivo(novo_nome)
                        caminho_final = os.path.join(PASTA_DOWNLOAD, novo_nome)
                        
                        if os.path.exists(caminho_final):
                            try: os.remove(caminho_final)
                            except: pass
                        
                        os.rename(arquivo_novo, caminho_final)
                        print(f" -> SUCESSO: {novo_nome}")
                        return True
                except:
                    pass
        sleep(1)
        tempo_decorrido += 1
    return False

# --- MAIN ATUALIZADO ---
def main():
    options = Options()
    prefs = {
        "download.default_directory": PASTA_DOWNLOAD,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # Login e Setup (Mantidos)
        driver.set_window_position(2000, 0)
        sleep(0.5)
        driver.maximize_window()
        driver.get("https://ebmsucesso.codefi.com.br/Acesso/Entrar?ReturnUrl=%2F")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='text']"))).send_keys("rubens.prudencini")
        driver.find_element(By.XPATH, "//input[@type='password']").send_keys("rLSP@0711")
        driver.find_element(By.XPATH, "//button[contains(., 'Entrar')]").click()
        sleep(5) 
        
        print("Acessando Menu Folha...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'title') and normalize-space(text())='Folha']"))).click()
        sleep(1)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'title') and contains(text(), 'Folha Pagamento')]"))).click()
        sleep(4)

        print("Lendo lista...")
        elementos_lista = driver.find_elements(By.XPATH, "//tr | //div[contains(@class, 'list')]//div[contains(@class, 'item')]")
        
        itens_para_processar = []
        historico = carregar_historico()

        for elem in elementos_lista:
            texto = elem.text.strip()
            if not texto: continue
            id_obra, nome_obra, competencia = extrair_detalhes(texto)
            if competencia and competencia >= '2025/12':
                itens_para_processar.append({'id': id_obra, 'nome': nome_obra, 'competencia': competencia})

        print(f"Total a processar: {len(itens_para_processar)}")

        for item in itens_para_processar:
            chave_hist = f"{item['id']}_{item['competencia']}"
            
            # if chave_hist in historico: continue

            print(f"--- Processando: {item['nome']} ({item['competencia']}) ---")
            
            sucesso_item = False
            
            for tentativa in range(1, MAX_TENTATIVAS + 1):
                try:
                    fechar_popup_se_existir(driver)
                    arquivos_antes = obter_arquivos_xlsx()

                    xpath_link = f"//a[contains(@href, '/FolhaPagamento/Consultar/{item['id']}')]"
                    
                    try:
                        link_obra = wait.until(EC.presence_of_element_located((By.XPATH, xpath_link)))
                    except TimeoutException:
                        print(" -> Link sumiu. Recarregando lista...")
                        driver.get("https://ebmsucesso.codefi.com.br/FolhaPagamento")
                        sleep(4)
                        link_obra = driver.find_element(By.XPATH, xpath_link)

                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link_obra)
                    sleep(1)
                    driver.execute_script("arguments[0].click();", link_obra)
                    sleep(3) 

                    # --- AQUI ESTÁ A CORREÇÃO DO BUG DO SISTEMA ---
                    # Verifica se apareceu pop-up logo ao entrar
                    if fechar_popup_se_existir(driver):
                        print(" -> [BUG DETECTADO] Pop-up encontrado. Aplicando Refresh (F5)...")
                        driver.refresh()
                        sleep(5) # Espera recarregar a página
                        # Verifica se o pop-up voltou após o refresh (as vezes volta)
                        fechar_popup_se_existir(driver)

                    # Verifica erro crítico
                    if "Erro" in driver.title:
                        raise Exception("Tela de erro crítico.")

                    # Tenta Exportar
                    try:
                        wait_botao = WebDriverWait(driver, 8)
                        btn_exportar = wait_botao.until(EC.presence_of_element_located((By.ID, "exportarRelatorioFolhaPagamento")))
                        
                        fechar_popup_se_existir(driver) # Check final antes do clique
                        
                        driver.execute_script("arguments[0].click();", btn_exportar)
                        
                        if esperar_novo_arquivo_e_renomear(arquivos_antes, item['nome'], item['competencia']):
                            historico[chave_hist] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            salvar_historico(historico)
                            sucesso_item = True
                            driver.back()
                            sleep(1)
                            break 
                        else:
                            # Se não baixou, verifica se apareceu pop-up AO CLICAR
                            if fechar_popup_se_existir(driver):
                                print(" -> Erro apareceu ao tentar baixar. Tentando refresh...")
                                driver.refresh()
                                sleep(4)
                                # Lança erro para cair no 'except' e tentar de novo no loop de tentativa
                                raise Exception("Pop-up ao baixar. Necessário retry.")
                            else:
                                raise Exception("Download não iniciou.")

                    except TimeoutException:
                        print(" -> [AVISO] Sem dados para exportar.")
                        sucesso_item = True
                        driver.back()
                        sleep(1)
                        break

                except Exception as e:
                    print(f" -> Tentativa {tentativa} falhou: {str(e)[:100]}...") # Log curto
                    if "FolhaPagamento" not in driver.current_url:
                        driver.get("https://ebmsucesso.codefi.com.br/FolhaPagamento")
                    else:
                        driver.refresh()
                    sleep(4)
            
            if not sucesso_item:
                print(f" [FALHA] Ignorando {item['nome']} após erros.")

    except Exception as e:
        print(f"ERRO GERAL: {e}")

if __name__ == "__main__":
    main()