import rospy

from artigo_framework.path_planning_client      import path_planning_client
from artigo_framework.control_manager_client    import control_manager_client
from artigo_framework.sensors_client            import Sensors

class Controle:
    def __init__(
        self            ,
        mapa_inicio_x   ,
        mapa_inicio_y   ,
        mapa_largura    ,
        mapa_altura     ,
        altura_coverage ,
        altura_foto     ,
        precisao        ):

        self.mapa_inicio_x      = mapa_inicio_x                             # Coordenada X do canto inferior esquerdo do mapa
        self.mapa_inicio_y      = mapa_inicio_y                             # Coordenada Y do canto inferior esquerdo do mapa
        self.mapa_largura       = mapa_largura                              # Largura do mapa
        self.mapa_altura        = mapa_altura                               # Altura do mapa
        self.altura_coverage    = altura_coverage                           # Altura da visão no coverage
        self.altura_foto        = altura_foto                               # Altura da visão nas fotos das algas
        self.precisao           = precisao                                  # Margem de erro para alcançar os objetivos 
        self.coverage_x         = []                                        # Coordenadas X do covarege
        self.coverage_y         = []                                        # Coordenadas Y do covarege
        self.coverage_posicao   = 0                                         # Posição atual no covarege
        self.algas_x            = []                                        # Coordenadas X das algas
        self.algas_y            = []                                        # Coordenadas Y das algas
        self.algas_posicao      = 0                                         # Posição da alga atual
        self.estado             = 0                                         # Estado atual do controlador
        self.sensor             = Sensors("ground_truth")                   # Contém informações dos sensores
        self.percorrido_x       = []                                        # Coordenada X do caminho percorrido pelo drone
        self.percorrido_y       = []                                        # Coordenada Y do caminho percorrido pelo drone
        self.camera_largura     = self.dimensoes_camera(altura_coverage)[0] # Largura da câmera
        self.camera_altura      = self.dimensoes_camera(altura_coverage)[1] # Altura da câmera

    def dimensoes_camera(self, alturaZ):
        K = [215.6810060961547, 0.0, 376.5, 0.0, 215.6810060961547, 240.5, 0.0, 0.0, 1.0]
        baseTerrestreAltura = 0.000009 # 0.5
        Z = alturaZ - baseTerrestreAltura # Distancia do solo
        dX = (0 - K[2]) * Z / K[0]
        dY = (0 - K[5]) * Z / K[4]
        dist = (0 - dX, 0 - dY)

        return 2 * dist[0], 2 * dist[1]

    def incrementar_caminho_percorrido(self, x, y):
        self.percorrido_x.append(x)
        self.percorrido_y.append(y)

    def salvar_caminho_percorrido(self, arquivo):
        with open(arquivo, "w") as file:
            for i in range(len(self.percorrido_x)):
                file.write("x=%6.1lf y=%6.1lf", self.percorrido_x[i], self.percorrido_y[i])

    def path_planning_coverage(self):
        # Requisição do caminho para o path_planning_server
        self.coverage_x, self.coverage_y = path_planning_client(
            self.mapa_inicio_x   ,
            self.mapa_inicio_y   ,
            self.mapa_largura    ,
            self.mapa_altura     ,
            self.camera_largura  ,
            self.camera_altura   )

        caminho_x_comprimento = len(self.coverage_x)
        caminho_y_comprimento = len(self.coverage_y)

        if caminho_x_comprimento == caminho_y_comprimento > 0:
            self.coverage_posicao = -1 # A próximo coordenada será a inicial
            return True
        else:
            return False

    def mover_para_proxima_posicao_coverage(self):
        if self.coverage_terminou():
            return False
        else:
            x = self.coverage_x[self.coverage_posicao]
            y = self.coverage_y[self.coverage_posicao]
            z = self.altura_coverage

            # Emitir ordem de movimento para o control_manager
            return control_manager_client(x, y, z)

    def destino_alcancado_coverage(self):
        objetivo_x = self.coverage_x[self.coverage_posicao]
        objetivo_y = self.coverage_y[self.coverage_posicao]
        objetivo_z = self.altura_coverage

        # Obter a posição atual
        atual_x, atual_y, atual_z = self.sensor.posicao_atual()

        alcancou_x = objetivo_x - self.precisao < atual_x < objetivo_x + self.precisao
        alcancou_y = objetivo_y - self.precisao < atual_y < objetivo_y + self.precisao
        alcancou_z = objetivo_z - self.precisao < atual_z < objetivo_z + self.precisao
        
        if alcancou_x and alcancou_y and alcancou_z:
            self.incrementar_caminho_percorrido(atual_x, atual_y)
            return True
        else:
            return False

    def coverage_terminou(self):
        if self.coverage_posicao >= len(self.coverage_x):
            return True
        else:
            return False

    def path_planning_algas(self):
         # Requisição do caminho para o algae_coord_service
        self.algas_x, self.algas_y = self.sensor.path_planning_algas()

        caminho_x_comprimento = len(self.algas_x)
        caminho_y_comprimento = len(self.algas_y)

        if caminho_x_comprimento == caminho_y_comprimento > 0:
            self.coverage_posicao = -1 # A próximo coordenada será a inicial
            return True
        elif caminho_x_comprimento == caminho_y_comprimento:
            self.coverage_posicao = 0
            return True
        else:
            return False

    def mover_para_proxima_alga(self):
        if self.monitoramento_terminou():
            return False
        else:
            x = self.algas_x[self.algas_posicao]
            y = self.algas_y[self.algas_posicao]
            z = self.altura_foto

            # Emitir ordem de movimento para o control_manager
            return control_manager_client(x, y, z)

    def destino_alcancado_alga(self):
        objetivo_x = self.algas_x[self.algas_posicao]
        objetivo_y = self.algas_y[self.algas_posicao]
        objetivo_z = self.altura_foto

        # Obter a posição atual
        atual_x, atual_y, atual_z = self.sensor.posicao_atual()

        alcancou_x = objetivo_x - self.precisao < atual_x < objetivo_x + self.precisao
        alcancou_y = objetivo_y - self.precisao < atual_y < objetivo_y + self.precisao
        alcancou_z = objetivo_z - self.precisao < atual_z < objetivo_z + self.precisao
        
        if alcancou_x and alcancou_y and alcancou_z:
            self.incrementar_caminho_percorrido(atual_x, atual_y)
            return True
        else:
            return False

    def monitoramento_terminou(self):
        if self.algas_posicao >= len(self.algas_x):
            return True
        else:
            return False

    def update_estado(self):

        if self.estado == 0: # Solicitar o caminho para o coverage
            rospy.loginfo("Dimensão das imagens capturadas pela câmera: %.1lf m X %.1lf m", self.camera_largura, self.camera_altura)
            rospy.loginfo("Solicitando o caminho para o coverage")
            sucesso = self.path_planning_coverage()
            if sucesso:
                rospy.loginfo("Caminho obtido")
                self.estado = 1
            else:
                rospy.loginfo("Erro ao obter o caminho para o coverage")

        elif self.estado == 1: # Tentar avançar no coverage
            self.coverage_posicao += 1
            if not self.coverage_terminou():
                self.estado = 2
            else:
                rospy.loginfo("Todos os pontos do coverage foram visitados")
                self.estado = 8

        elif self.estado == 2: # Emitir ordem de movimento para a próxima posição no coverage
            rospy.loginfo("Emitindo ordem de movimento para a próxima posição no coverage")
            sucesso = self.mover_para_proxima_posicao_coverage()
            if sucesso:
                self.estado = 3

        elif self.estado == 3: # Aguardar o destino
            rospy.loginfo("Aguardando destino")
            if self.destino_alcancado_coverage():
                rospy.loginfo("Destino alcançado")
                self.estado = 4
        
        elif self.estado == 4: # Solicitar o caminho para fotografar as algas
            rospy.loginfo("Solicitando o caminho para fotografar as algas")
            sucesso = self.path_planning_algas()
            if sucesso:
                rospy.loginfo("Caminho obtido")
                self.estado = 5

        elif self.estado == 5: # Verificar se todas as algas foram fotografadas
            self.algas_posicao += 1
            if not self.monitoramento_terminou():
                self.estado = 6
            else:
                rospy.loginfo("Todas as algas foram fotografadas")
                self.estado = 1

        elif self.estado == 6: # Emitir ordem de movimento para visitar a próxima alga
            rospy.loginfo("Emitindo ordem de movimento para a próxima alga")
            sucesso = self.mover_para_proxima_alga()
            if sucesso:
                self.estado = 7

        elif self.estado == 7: # Aguardar o destino
            rospy.loginfo("Aguardando destino")
            if self.destino_alcancado_alga():
                rospy.loginfo("Destino alcançado")
                self.estado = 5

        elif self.estado == 8: # Salvar o caminho
            self.salvar_caminho_percorrido("caminho.txt")
            rospy.loginfo("O caminho foi salvo")
            rospy.loginfo("Fim da execução")
            self.estado = 9

        else:
            pass
