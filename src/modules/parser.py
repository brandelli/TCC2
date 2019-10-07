import csv
from helpers import file_helper, validator_helper, data_process_helper, dictionary_creator_helper

class Parser:

    relation_id = 0
    word_id = 1
    entity_type_id = 0

    def __init__(self, config):
        self.config = config

    
    def get_config(self, str_config_type=None):
        return self.config.get_configuration(str_config_type)


    def increment_relation_id(self, inc=1):
        '''
        Função para incrementar o relation_id
        '''
        self.relation_id += inc


    def increment_word_id(self, inc=1):
        '''
        Função para incrementar o word_id
        '''
        self.word_id += inc


    def increment_entity_type_id(self, inc=1):
        self.entity_type_id += inc

    
    def run_initial_parse(self):
        '''
        Função chamada ao iniciar o programa,
        realiza o parse dos arquivos conforme as configurações
        '''
        # chamada para conversão de arquivos originais(txt, tsv) para json
        self.convert_src_to_json_files()

        # chamada para criação de dicionários: word_to_id e reverse_dict
        self.create_word_dicts()

        # chamada para formatação de inputs que serão utilizados pelo modelo
        self.parse_inputs_for_model()

        # chamada para adicionar padding nas sentenças de treino, para que todas tenham o mesmo tamanho
        self.prepare_dataset_for_padding()

        # chamada para criar vetores de relacionamentos que vão ser utilizados no input
        self.create_relations_input()

        # chamada para criar o vetor posicional que pode ser utilizado no input
        self.create_positional_vector(['train', 'test'])

        self.create_relative_position_entities_vector()

        # chamada para criar parametro com tupla contendo o tipo de cada entidadade
        self.create_entities_type_input(['train', 'test'])

        # chamada para criar o vetor de output que será utilizado no treino do modelo
        self.create_output_for_model()

    
    def create_relative_position_entities_vector(self):
        input_config = self.get_config('input_for_model')
        input_path = input_config.get('path')
        dataset_config = self.get_config('dataset')
        dataset_path = dataset_config.get('path')
        data_types = ['train', 'test']
        for data_type in data_types:
            dataset_file = 'train_json' if data_type == 'train' else 'test_json'
            input_sentences_file = 'train_sentence_input' if data_type == 'train' else 'test_sentence_input' 
            input_sentences_data = file_helper.get_json_file_data(input_path, input_config.get(input_sentences_file))
            input_e1_file = 'train_relative_position_e1_input' if data_type == 'train' else 'test_relative_position_e1_input'
            input_e2_file = 'train_relative_position_e2_input' if data_type == 'train' else 'test_relative_position_e2_input'
            dataset = file_helper.get_json_file_data(dataset_path, dataset_config.get(dataset_file))
            position_e1, position_e2 = self.create_relative_vectors(dataset, input_sentences_data)
            file_helper.dict_to_json(input_path, input_config.get(input_e1_file), position_e1, 4)
            file_helper.dict_to_json(input_path, input_config.get(input_e2_file), position_e2, 4)


    def create_relative_vectors(self, dataset, input_sentences_data):
        position_e1 = []
        position_e2 = []
        greatest_len = data_process_helper.get_longest_sentence_from_dataset(input_sentences_data)
        print(f'greatest_len: {greatest_len}')
        for data in dataset:
            sentence = data.get('sentence')
            e1 = greatest_len * [0]
            e2 = greatest_len * [0]
            head = data.get('head').get('word')
            tail = data.get('tail').get('word')
            pos_e1 = (sentence.index(head) + 1) * (-1)
            pos_e2 = (sentence.index(tail) + 1) * (-1)
            cur_e1 = []
            cur_e2 = []
            for _ in e1:
                pos_e1 += 1 
                cur_e1.append(pos_e1)
            for _ in e2:
                pos_e2 += 1 
                cur_e2.append(pos_e2)
            position_e1.append(cur_e1)
            position_e2.append(cur_e2)
        
        return position_e1, position_e2
            


    def create_entities_type_input(self, types_list):
        '''
        '''
        input_config = self.get_config('input_for_model')
        dataset_config = self.get_config('dataset')
        entities_config = self.get_config('entities')
        entities_type_id = file_helper.get_json_file_data(entities_config.get('path'), entities_config.get('entities_to_id'))
        for str_type in types_list:
            dataset_type = 'train_json' if str_type == 'train' else 'test_json'
            entity_input_type = 'train_entity_type_input' if str_type == 'train' else 'test_entity_type_input'
            sentences = file_helper.get_json_file_data(dataset_config.get('path'), dataset_config.get(dataset_type))
            entities_type_relation = []
            for sentence in sentences:
                head_type = sentence.get('head').get('category')
                tail_type = sentence.get('tail').get('category')
                entities_type_relation.append([entities_type_id.get(head_type), entities_type_id.get(tail_type)])

            file_helper.dict_to_json(input_config.get('path'), input_config.get(entity_input_type), entities_type_relation, 4)


    def create_positional_vector(self, types_list):
        '''
        Cria o arquivo de vetor posicional de entidade, com a seguinte representação:
            * 0 -> palavra normal
            * 1 -> entidade

        Resultando no seguinte exemplo:
        [0, 0, 1, 0, 0, 1]
        '''
        input_config = self.get_config('input_for_model')
        path = input_config.get('path')
        for str_type in types_list:
            relations_type = 'train_relations_input' if str_type == 'train' else 'test_relations_input'
            sentences_type = 'train_sentence_input' if str_type == 'train' else 'test_sentence_input'
            positional_vector_type = 'train_positional_vector_input' if str_type == 'train' else 'test_positional_vector_input'
            relations_list = file_helper.get_json_file_data(path, input_config.get(relations_type))
            sentences_list = file_helper.get_json_file_data(path, input_config.get(sentences_type))
            positional_vector = []
            for index, sentence in enumerate(sentences_list, start=0):
                current_sentence = []
                for word in sentence:
                    current_sentence.append(int(word in relations_list[index]))
                positional_vector.append(current_sentence)
            
            file_helper.dict_to_json(path, input_config.get(positional_vector_type), positional_vector, 4)


    
    def create_word_embeddings_weight(self):
        '''
        Função para criar o arquivo com vetor de pesos do word embeddings que será utilizado no modelo
        '''
        word_embeddings_config = self.get_config('word_embeddings')
        word_embeddings = file_helper.get_json_file_data(word_embeddings_config.get('path'), word_embeddings_config.get('word_embeddings_json'))
        word_embeddings_dimension = word_embeddings_config.get('dimensions')
        word_to_id_config = self.get_config('word_to_id')
        word_to_id = file_helper.get_json_file_data(word_to_id_config.get('path'), word_to_id_config.get('dict'))
        word_embeddings_weight = self.create_empty_word_embeddings_weight_list(len(word_to_id) + 1, word_embeddings_dimension) 
        for word, index in word_to_id.items():
            weight_in_embeddings = word_embeddings.get(word)
            if weight_in_embeddings is not None:
                word_embeddings_weight[index] = weight_in_embeddings
        
        input_for_model_config = self.get_config('input_for_model')
        file_helper.dict_to_json(input_for_model_config.get('path'), input_for_model_config.get('word_embeddings_weight'), word_embeddings_weight, 4)


    def create_empty_word_embeddings_weight_list(self, vocab_size, embeddings_dimension):
        embeddings_weight = []
        for _ in range(vocab_size):
            embeddings_weight.append([0] * int(embeddings_dimension))
        
        return embeddings_weight


    def create_output_for_model(self):
        '''
        Cria o arquivo de output do modelo
        '''
        output_for_model_config = self.get_config('output')
        path = output_for_model_config.get('path')
        dataset_types = ['train', 'test']
        for str_type in dataset_types:
            dataset_type = 'train_relation_output' if str_type == 'train' else 'test_relation_output'
            file_name = output_for_model_config.get(dataset_type)
            output_data = self.create_relation_classification_output(str_type)
            file_helper.dict_to_json(path, file_name, output_data, 4)


    def create_relation_classification_output(self, str_dataset_type):
        '''
        Cria uma estrutura com o relacionamento que deve ser apresentado como output do modelo
        '''
        dataset_config = self.get_config('dataset')
        relation_config = self.get_config('relation')
        relation_data = file_helper.get_json_file_data(relation_config.get('path'), relation_config.get('file_name'))
        relation_classification = []
        path = dataset_config.get('path')
        dataset_type = 'train_json' if str_dataset_type == 'train' else 'test_json'
        file_name = dataset_config.get(dataset_type)
        data = file_helper.get_json_file_data(path, file_name)
        for sentence in data:
            relation = sentence.get('relation')
            if(relation_data.get(relation) == None):
                relation_classification.append(0)
            else:
                relation_classification.append(relation_data.get(relation))
        
        return relation_classification


    def create_relations_input(self):
        '''
        Cria o arquivo json com as relações presentes nas senteças, e devem ser utilizadas
        como input no modelo
        '''
        input_for_model_config = self.get_config('input_for_model')
        path = input_for_model_config.get('path')
        dataset_config = self.get_config('dataset')
        train_file_name = input_for_model_config.get('train_relations_input')
        test_file_name = input_for_model_config.get('test_relations_input')
        relations_input_train_data = self.create_individual_relations_input(dataset_config, 'train')
        relations_input_test_data = self.create_individual_relations_input(dataset_config, 'test')
        file_helper.dict_to_json(path, train_file_name, relations_input_train_data, 4)
        file_helper.dict_to_json(path, test_file_name, relations_input_test_data, 4)

    
    def create_individual_relations_input(self, dataset_config, dataset_type):
        relations_list = []
        path = dataset_config.get('path')
        if dataset_type == 'train':
            data = file_helper.get_json_file_data(path, dataset_config.get('train_json'))
        else:
            data = file_helper.get_json_file_data(path, dataset_config.get('test_json'))
        
        for sentence in data:
            entities = []
            entities.append(sentence.get('head').get('id'))
            entities.append(sentence.get('tail').get('id'))
            relations_list.append(entities)
        
        return relations_list

    
    def prepare_dataset_for_padding(self):
        '''
        Função para adicionar padding nas sentenças de treino, para que todas tenham o mesmo tamanho
        '''
        input_for_model_config = self.get_config('input_for_model')
        path = input_for_model_config.get('path')
        input_types = ['train', 'test']
        for str_type in input_types:
            input_type = 'train_sentence_input' if str_type == 'train' else 'test_sentence_input'
            file_name = input_for_model_config.get(input_type)
            input_data = file_helper.get_json_file_data(path, file_name)
            lenght = data_process_helper.get_longest_sentence_from_dataset(input_data)
            self.include_padding(input_data, lenght)
            file_helper.dict_to_json(path, file_name, input_data, 4)

    
    def include_padding(self, data, padding):
        '''
        Adiciona a representação de paddings na sentença -> word_to_id = 0
        '''
        for sentence in data:
            while len(sentence) < padding:
                sentence.append(0)
    

    def parse_inputs_for_model(self):
        '''
        Função para parsear o input de palavras para numeros, tornando melhor para alimentar o modelo
        '''
        word_to_id_config = self.get_config('word_to_id')
        word_to_id_path = word_to_id_config.get('path')
        word_to_id_file_name = word_to_id_config.get('dict')
        word_to_id = file_helper.get_json_file_data(word_to_id_path, word_to_id_file_name)
        relation_config = self.get_config('relation')
        relation_path = relation_config.get('path')
        relation_file_name = relation_config.get('file_name')
        relation_dict = file_helper.get_json_file_data(relation_path, relation_file_name)
        self.parse_dataset_for_model('train', word_to_id, relation_dict)
        self.parse_dataset_for_model('test', word_to_id, relation_dict)
        self.create_word_embeddings_weight()
        
    
    def parse_dataset_for_model(self, dataset_type, word_to_id, relation_dict):
        '''
        Função para iniciar o processo de parseamento dos datasets, para se adequar ao modelo
        '''
        input_for_model_config = self.get_config('input_for_model')
        dataset_config = self.get_config('dataset')
        input_for_model_path = input_for_model_config.get('path')
        dataset_path = dataset_config.get('path')
        str_input_file_name = 'train_sentence_input' if dataset_type == 'train' else 'test_sentence_input'
        str_sentences_dict = 'train_json' if dataset_type == 'train' else 'test_json'
        str_label_file_name = 'train_sentence_label' if dataset_type == 'train' else 'test_sentence_label'
        input_file_name = input_for_model_config.get(str_input_file_name)
        sentences_dict = file_helper.get_json_file_data(dataset_path, dataset_config.get(str_sentences_dict))
        label_file_name = input_for_model_config.get(str_label_file_name)
        parsed_sentence_list, parsed_relation_list = self.parse_sentence_for_model(sentences_dict, word_to_id, relation_dict)
        file_helper.dict_to_json(input_for_model_path, input_file_name, parsed_sentence_list, None)
        file_helper.dict_to_json(input_for_model_path, label_file_name, parsed_relation_list, 4)

    
    def parse_sentence_for_model(self, sentences_dict, word_id, relation_dict):
        '''
        Função para recuperar o valor numérico de relacionamente e palavras presentes nas sentenças
        '''
        parsed_sentence_list = []
        parsed_relation_list = []
        for sentence_dict in sentences_dict:
            words_list = []
            sentence = sentence_dict.get('sentence')
            relation = sentence_dict.get('relation')
            for word in sentence.split(' '):
                words_list.append(word_id.get(word))

            parsed_sentence_list.append(words_list)
            parsed_relation_list.append(relation_dict.get(relation))

        return parsed_sentence_list, parsed_relation_list


    def create_word_dicts(self):
        '''
        Função que cria os dicionários de palavras(word_to_id, reverse_dict) presentes nos dados de entrada
        '''
        word_to_id_config = self.get_config('word_to_id')
        path = word_to_id_config.get('path')
        word_to_id_file_name = word_to_id_config.get('dict')
        reverse_dict_file_name = word_to_id_config.get('reverse_dict')
        word_to_id_dict = {}
        reverse_dict = {}
        self.process_all_dataset_to_word_to_id(word_to_id_dict, reverse_dict)
        file_helper.dict_to_json(path, word_to_id_file_name, word_to_id_dict, 4)
        file_helper.dict_to_json(path, reverse_dict_file_name, reverse_dict, 4)
        
    
    def convert_src_to_json_files(self):
        '''
        Função que realiza a conversão dos arquivos de entrada para json
        '''
        # transforma o arquivo txt de word embeddings em um json
        self.word_embeddings_to_json()

        # transforma o arquivo de dataset de treino em json
        self.dataset_to_json('train')
        
        # transforma o arquivo de dataset de test em json
        self.dataset_to_json('test')

        # cria um arquivo json com os relacionamentos presentes no dataset de treino
        self.relation_to_id_json()

        # cria im arquivo json com todos os tipos de entidades presente
        self.entities_types_to_id()


    def entities_types_to_id(self):
        '''
        Cria os dicionários para os tipos de entidades presentes no dataset de treino
        '''
        entities_type_dict = {}
        reverse_entities_type_dict = {}
        dataset_config = self.get_config('dataset')
        train_dataset = file_helper.get_json_file_data(dataset_config.get('path'), dataset_config.get('train_json'))
        for sentence in train_dataset:
            self.add_data_to_entities_dict('head', sentence, entities_type_dict, reverse_entities_type_dict)
            self.add_data_to_entities_dict('tail', sentence, entities_type_dict, reverse_entities_type_dict)
        
        entities_config = self.get_config('entities')
        path = entities_config.get('path')
        file_helper.dict_to_json(path, entities_config.get('entities_to_id'), entities_type_dict, 4)
        file_helper.dict_to_json(path, entities_config.get('reverse_entities_to_id'), reverse_entities_type_dict, 4)


    def add_data_to_entities_dict(self, str_entity, sentence, entity_to_id_dict, reverse_dict):
        '''
        Adiciona os dados nos dicionarios de entidades
        '''
        entity = sentence.get(str_entity).get('category')
        if entity_to_id_dict.get(entity) is None:
            entity_to_id_dict[entity] = self.entity_type_id
            reverse_dict[self.entity_type_id] = entity
            self.increment_entity_type_id()
        

    def dataset_to_json(self, dataset_type):
        '''
        Função para transformar os inputs do dataset em json
        '''
        # vai guardar o index de cada uma das chaves presentes no cabeçalho do arquivo
        dataset_config = self.get_config('dataset')
        keys_dict = {}
        dataset_list = []
        path = dataset_config.get('path')
        str_file_name = 'train_tsv' if dataset_type == 'train' else 'test_tsv'
        str_json_file_name = 'train_json' if dataset_type == 'train' else 'test_json'
        file_name = dataset_config.get(str_file_name)
        json_file_name = dataset_config.get(str_json_file_name)
        
        with open(f"{path}{file_name}") as fp:
            # faz a leitura do arquivo, utilizando a tabulação como separeador
            reader = csv.reader(fp, delimiter="\t")
            # a primeira linha contém as chaves de cada um dos campos
            keys = reader.__next__()

            # preenche o dicionario de chaves com o indice
            for index, value in enumerate(keys, start=0):
                keys_dict[index] = value.lower()
            
            # para as outras linhas do arquivo vai adicionando cada campo em seu respectivo lugar
            for line in reader:
                cur_dict = dictionary_creator_helper.create_dataset_dict()
                for index, value in enumerate(line):
                    self.process_dataset_data(cur_dict, keys_dict.get(index), value)

                dataset_list.append(cur_dict)
                    
        file_helper.dict_to_json(path, json_file_name, dataset_list, 4)


    def process_dataset_data(self, cur_dict, key, value):
        '''
        Função para processar os dados do dataset de acordo com os campos
        '''
        if validator_helper.is_id_data(key):
            data_process_helper.process_id_data(cur_dict, key, value)
        elif validator_helper.is_entity(key):
            data_process_helper.process_entity_data(cur_dict, key, value)
        elif validator_helper.is_category(key):
            data_process_helper.process_category_data(cur_dict, key, value)
        elif validator_helper.is_sentence(key):
            data_process_helper.process_sentence_data(cur_dict, key, value)
        elif validator_helper.is_relation(key):
            data_process_helper.process_relation_data(cur_dict, key, value)


    def word_embeddings_to_json(self):
        '''
        Função para transformar o arquivo de word_embeddings em json
        '''
        word_embeddings_config = self.get_config('word_embeddings')
        # lista de dicionarios com dados processados de word embeddings
        word_embeddings_dict = {}
        path = word_embeddings_config.get('path')
        # seta o arquivo que vai ser utilizado de word embeddings
        src_word_embedings = 'real_src' if word_embeddings_config.get('real') else 'example_src'
        file_name = word_embeddings_config.get(src_word_embedings)
  
        with open(f"{path}{file_name}") as fp:
            # primeira linha do arquivo contém o número de linhas e a dimensionalidade do vetor
            lines, vector_size = fp.readline().strip().split(' ')
            word_embeddings_config['vocab_size'] = lines
            word_embeddings_config['dimensions'] = vector_size
            # itera por todas linhas que contém dados do word embeddings
            for _ in range(int(lines)):
                # separa os dados presentes em cada linha, e realiza o pop para separar a word do vetor
                data_list = fp.readline().strip().split(' ')
                word = data_list[0]
                # transforma os dados do vetor em float
                word_embeddings_dict[word] = [float(x) for x in data_list[1:]]
        
        json_file_name = word_embeddings_config.get('word_embeddings_json')
        file_helper.dict_to_json(path, json_file_name, word_embeddings_dict, 4)


    def relation_to_id_json(self):
        '''
        Função para atribuir um id para cada uma das relações encontradas no dataset de treino
        '''
        dataset_config = self.get_config('dataset')
        treino_json = file_helper.get_json_file_data(dataset_config.get('path'), dataset_config.get('train_json'))
        relation_config = self.get_config('relation')
        relation_dict = {}
        # primeira relação deve ser NA e o id 0
        relation_dict['NA'] = self.relation_id
        for line in treino_json:
            relation = line.get('relation')
            if relation_dict.get(relation) is None:
                self.increment_relation_id()
                relation_dict[relation] = self.relation_id
        
        file_helper.dict_to_json(relation_config.get('path'), relation_config.get('file_name'), relation_dict, 4)


    def add_word_to_id(self, word, word_to_id_dict, reverse_dict):
        '''
        Função para adicionar um id para uma palavra
        '''
        if word_to_id_dict.get(word) is None:
            word_to_id_dict[word] = self.word_id
            reverse_dict[self.word_id] = word
            self.increment_word_id()


    def add_word_embeddings_to_word_to_id(self, word_embeddings_config, word_to_id_dict, reverse_dict):
        '''
        Função para atribuir e adicionar ids das palavras encontradas no word embeddings
        '''
        path = word_embeddings_config.get('path')
        file_name = word_embeddings_config.get('word_embeddings_json')
        word_embeddings = file_helper.get_json_file_data(path, file_name)
        for line in word_embeddings:
            self.add_word_to_id(line.get('word'), word_to_id_dict, reverse_dict)
    

    def process_all_dataset_to_word_to_id(self, word_to_id_dict, reverse_dict):
        '''
        Função para iniciar o processamento de todos os datasets (treino, teste)
        para word_to_id
        '''
        dataset_config = self.get_config('dataset')
        path = dataset_config.get('path')
        train_file_name = dataset_config.get('train_json')
        test_file_name = dataset_config.get('test_json')
        self.process_individual_dataset_to_word_to_id(path, train_file_name, word_to_id_dict, reverse_dict)
        self.process_individual_dataset_to_word_to_id(path, test_file_name, word_to_id_dict, reverse_dict)

    
    def process_individual_dataset_to_word_to_id(self, path, file_name, word_to_id_dict, reverse_dict):
        '''
        Função para processar individualmente cada um dos datasets em word_to_id e reverse_dict
        '''
        dict_data = file_helper.get_json_file_data(path, file_name)
        self.add_dataset_to_word_to_id(dict_data, word_to_id_dict, reverse_dict)
        file_helper.dict_to_json(path, file_name, dict_data, 4)
    

    def add_dataset_to_word_to_id(self, dataset, word_to_id_dict, reverse_dict):
        '''
        Função para transformar todas palavras das frases presentes 
        no dataset em word_to_id
        '''
        for line in dataset:
            sentence = line.get('sentence')
            for word in sentence.split(' '):
                self.add_word_to_id(word, word_to_id_dict, reverse_dict)
            
            self.set_word_id_to_entity_in_dataset(line, word_to_id_dict)
    

    def set_word_id_to_entity_in_dataset(self, dataset_line, word_to_id_dict):
        head = dataset_line.get('head')
        tail = dataset_line.get('tail')
        head['id'] = word_to_id_dict.get(head.get('word'))
        tail['id'] = word_to_id_dict.get(tail.get('word'))

