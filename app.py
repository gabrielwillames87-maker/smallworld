import streamlit as st
import requests

# 1. Configuração da página
st.set_page_config(page_title="Small World Bridge Finder", layout="wide")

# ==========================================================
# SISTEMA DE LOGIN
# ==========================================================
# Inicializa o estado de login na memória da sessão
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Se não estiver logado, mostra a tela de login e para a execução do app
if not st.session_state["logged_in"]:
    st.title("🔒 Acesso Restrito")
    st.write("Por favor, insira suas credenciais para acessar a ferramenta.")
    
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if usuario == "small" and senha == "world":
            st.session_state["logged_in"] = True
            st.rerun() # Recarrega a página para liberar o app
        else:
            st.error("Usuário ou senha incorretos.")
            
    st.stop() # Bloqueia o carregamento do resto do código até logar

# ==========================================================
# CÓDIGO PRINCIPAL DO APP (Só roda se logado)
# ==========================================================
st.title("🃏 Small World Bridge Finder")
st.write("Importe seu arquivo `.ydk` e descubra suas linhas de Small World!")

# Cache de 24 horas (86400 segundos) para não sobrecarregar a API
@st.cache_data(ttl=86400)
def fetch_card_data():
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    
    # Política de bom uso: Identificação do App
    headers = {
        "User-Agent": "SmallWorldBridgeFinder_Personal/1.0"
    }
    
    response = requests.get(url, headers=headers).json()
    
    # Cria um dicionário mapeando o ID para os status da carta
    card_dict = {}
    for card in response['data']:
        if 'Monster' in card['type']: # Só nos interessam monstros
            card_info = {
                'name': card['name'],
                'type': card['race'],
                'attribute': card.get('attribute', ''),
                'level': card.get('level', 0),
                'atk': card.get('atk', 0),
                'def': card.get('def', 0),
                'image': card['card_images'][0]['image_url_small']
            }
            # Salva o ID principal
            card_dict[str(card['id'])] = card_info
            # Salva também as Artes Alternativas
            for img in card['card_images']:
                card_dict[str(img['id'])] = card_info
                
    return card_dict

all_monsters = fetch_card_data()

# Função para testar a condição do Small World
def check_small_world_match(c1, c2):
    matches = 0
    if c1['type'] == c2['type']: matches += 1
    if c1['attribute'] == c2['attribute']: matches += 1
    if c1['level'] == c2['level']: matches += 1
    if c1['atk'] == c2['atk'] and c1['atk'] is not None: matches += 1
    if c1['def'] == c2['def'] and c1['def'] is not None: matches += 1
    return matches == 1

# Upload do arquivo .ydk
uploaded_file = st.file_uploader("Escolha o arquivo .ydk do YGO Omega", type=["ydk"])

if uploaded_file:
    # Ler os IDs do arquivo de texto
    lines = uploaded_file.read().decode("utf-8").splitlines()
    deck_ids = []
    
    is_main = False
    for line in lines:
        if line.startswith("#main"):
            is_main = True
            continue
        if line.startswith("#extra") or line.startswith("!side"):
            is_main = False
        if is_main and line.strip().isdigit():
            deck_ids.append(line.strip())
            
    deck_monsters = {idx: all_monsters[idx] for idx in deck_ids if idx in all_monsters}
    
    if deck_monsters:
        monster_names = sorted(list(set([m['name'] for m in deck_monsters.values()])))
        
        st.write("---")
        # Escolha do modo de pesquisa
        modo_pesquisa = st.radio(
            "Como você quer montar a sua rota?",
            ["👉 Tenho na mão ➡️ Quero buscar", "🎯 Quero buscar ➡️ O que preciso na mão?"]
        )
        
        st.write("---")

        # ==========================================================
        # MODO 1: MÃO -> ALVO
        # ==========================================================
        if modo_pesquisa == "👉 Tenho na mão ➡️ Quero buscar":
            st.subheader("1. Escolha a carta na sua MÃO:")
            hand_card_name = st.selectbox("Selecionar monstro na mão:", monster_names)
            hand_card = next(m for m in deck_monsters.values() if m['name'] == hand_card_name)
            
            valid_lines = []
            for b_id, bridge_card in deck_monsters.items():
                if bridge_card['name'] == hand_card['name']: continue
                
                if check_small_world_match(hand_card, bridge_card):
                    for t_id, target_card in deck_monsters.items():
                        if target_card['name'] == hand_card['name'] or target_card['name'] == bridge_card['name']: 
                            continue
                            
                        if check_small_world_match(bridge_card, target_card):
                            valid_lines.append({
                                'bridge': bridge_card['name'],
                                'target': target_card['name'],
                                'target_img': target_card['image']
                            })
            
            st.subheader("🎯 Alvos Possíveis e suas Pontes:")
            if valid_lines:
                grouped_targets = {}
                for line in valid_lines:
                    if line['target'] not in grouped_targets:
                        grouped_targets[line['target']] = {'img': line['target_img'], 'bridges': set()}
                    grouped_targets[line['target']]['bridges'].add(line['bridge'])
                    
                cols = st.columns(4)
                for i, (target_name, data) in enumerate(grouped_targets.items()):
                    with cols[i % 4]:
                        st.image(data['img'], width=120)
                        st.markdown(f"**{target_name}**")
                        st.caption(f"Pontes: {', '.join(data['bridges'])}")
            else:
                st.warning("Nenhum alvo válido encontrado para essa carta.")

        # ==========================================================
        # MODO 2: ALVO -> MÃO
        # ==========================================================
        else:
            st.subheader("1. Escolha a carta que você QUER BUSCAR:")
            target_card_name = st.selectbox("Selecionar alvo desejado:", monster_names)
            target_card = next(m for m in deck_monsters.values() if m['name'] == target_card_name)
            
            valid_lines = []
            for b_id, bridge_card in deck_monsters.items():
                if bridge_card['name'] == target_card['name']: continue
                
                if check_small_world_match(target_card, bridge_card):
                    for h_id, hand_card in deck_monsters.items():
                        if hand_card['name'] == target_card['name'] or hand_card['name'] == bridge_card['name']: 
                            continue
                            
                        if check_small_world_match(bridge_card, hand_card):
                            valid_lines.append({
                                'bridge': bridge_card['name'],
                                'hand': hand_card['name'],
                                'hand_img': hand_card['image']
                            })
            
            st.subheader(f"🃏 Cartas que conectam até {target_card_name}:")
            if valid_lines:
                grouped_hands = {}
                for line in valid_lines:
                    if line['hand'] not in grouped_hands:
                        grouped_hands[line['hand']] = {'img': line['hand_img'], 'bridges': set()}
                    grouped_hands[line['hand']]['bridges'].add(line['bridge'])
                    
                cols = st.columns(4)
                for i, (hand_name, data) in enumerate(grouped_hands.items()):
                    with cols[i % 4]:
                        st.image(data['img'], width=120)
                        st.markdown(f"**{hand_name}**")
                        st.caption(f"Pontes: {', '.join(data['bridges'])}")
            else:
                st.warning("Nenhuma carta no deck consegue chegar nesse alvo.")

    else:
        st.error("Nenhum monstro válido encontrado no Main Deck do arquivo YDK.")
