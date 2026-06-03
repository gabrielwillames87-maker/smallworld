import streamlit as st
import requests

# 1. Configuração da página
st.set_page_config(page_title="Small World Bridge Finder", layout="wide")
st.title("🃏 Small World Bridge Finder")
st.write("Importe seu arquivo `.ydk` e descubra suas linhas de Small World!")

# Cache para não estourar o limite de requisições da API
@st.cache_data
def fetch_card_data():
    url = "https://db.ygoprodeck.com/api/v7/cardinfo.php"
    response = requests.get(url).json()
    
    # Cria um dicionário mapeando o ID para os status da carta
    card_dict = {}
    for card in response['data']:
        if 'Monster' in card['type']: # Só nos interessam monstros
            # Cria os status da carta
            card_info = {
                'name': card['name'],
                'type': card['race'], # No YGOPRODeck, 'race' é o Tipo (ex: Warrior)
                'attribute': card.get('attribute', ''),
                'level': card.get('level', 0),
                'atk': card.get('atk', 0),
                'def': card.get('def', 0),
                'image': card['card_images'][0]['image_url_small']
            }
            
            # Salva o ID principal da carta
            card_dict[str(card['id'])] = card_info
            
            # Salva também os IDs de todas as Artes Alternativas (Alt Arts)
            for img in card['card_images']:
                card_dict[str(img['id'])] = card_info
                
    return card_dict

all_monsters = fetch_card_data()

# 2. Função para testar a condição do Small World
def check_small_world_match(c1, c2):
    # Conta quantas características são IGUAIS
    matches = 0
    if c1['type'] == c2['type']: matches += 1
    if c1['attribute'] == c2['attribute']: matches += 1
    if c1['level'] == c2['level']: matches += 1
    if c1['atk'] == c2['atk'] and c1['atk'] is not None: matches += 1
    if c1['def'] == c2['def'] and c1['def'] is not None: matches += 1
    
    # Small World EXIGE exatamente uma correspondência
    return matches == 1

# 3. Upload do arquivo .ydk
uploaded_file = st.file_uploader("Escolha o arquivo .ydk do YGO Omega", type=["ydk"])

if uploaded_file:
    # Ler os IDs do arquivo de texto
    lines = uploaded_file.read().decode("utf-8").splitlines()
    deck_ids = []
    
    # Filtrar apenas a parte do Main Deck (ignora extra, side e linhas de texto)
    is_main = False
    for line in lines:
        if line.startswith("#main"):
            is_main = True
            continue
        if line.startswith("#extra") or line.startswith("!side"):
            is_main = False
        if is_main and line.strip().isdigit():
            deck_ids.append(line.strip())
            
    # Filtrar IDs duplicados e garantir que estão na base de monstros
    deck_monsters = {idx: all_monsters[idx] for idx in deck_ids if idx in all_monsters}
    
    if deck_monsters:
        # Criar uma lista para o selectbox
        monster_names = sorted(list(set([m['name'] for m in deck_monsters.values()])))
        
        st.subheader("1. Escolha a carta na sua MÃO:")
        hand_card_name = st.selectbox("Selecionar monstro:", monster_names)
        
        # Achar o objeto da carta da mão
        hand_card = next(m for m in deck_monsters.values() if m['name'] == hand_card_name)
        
        # 4. Processar as Pontes e Alvos
        valid_lines = []
        for b_id, bridge_card in deck_monsters.items():
            if bridge_card['name'] == hand_card['name']: continue # Ponte não pode ser a mesma carta
            
            if check_small_world_match(hand_card, bridge_card):
                # Se a mão conecta com a ponte, vamos ver com quem a ponte conecta no resto do deck
                for t_id, target_card in deck_monsters.items():
                    if target_card['name'] == hand_card['name'] or target_card['name'] == bridge_card['name']: 
                        continue
                        
                    if check_small_world_match(bridge_card, target_card):
                        valid_lines.append({
                            'bridge': bridge_card['name'],
                            'target': target_card['name'],
                            'target_img': target_card['image']
                        })
        
        # 5. Exibir os Resultados
        st.write("---")
        st.subheader("🎯 Alvos Possíveis e suas Pontes:")
        
        if valid_lines:
            # Agrupar por alvo para ficar bonito
            grouped_targets = {}
            for line in valid_lines:
                if line['target'] not in grouped_targets:
                    grouped_targets[line['target']] = {'img': line['target_img'], 'bridges': set()}
                grouped_targets[line['target']]['bridges'].add(line['bridge'])
                
            # Renderizar na tela em colunas
            cols = st.columns(4)
            for i, (target_name, data) in enumerate(grouped_targets.items()):
                with cols[i % 4]:
                    st.image(data['img'], width=120)
                    st.markdown(f"**{target_name}**")
                    st.caption(f"Pontes: {', '.join(data['bridges'])}")
        else:
            st.warning("Nenhum alvo válido encontrado para essa carta com as cartas atuais do deck.")
    else:
        st.error("Nenhum monstro válido encontrado no Main Deck do arquivo YDK.")
