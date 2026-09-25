import pygame
import sys
from config import WIDTH, HEIGHT, FPS, TITLE
from states import StateMachine, MenuState, ModeSelectState, HelpState, BattleState, GameOverState
from image_manager import load_element_images

def main():
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # Load images AFTER display is initialized
    load_element_images()

    machine = StateMachine()
    machine.add_state("menu", MenuState(machine))
    machine.add_state("mode_select", ModeSelectState(machine))
    machine.add_state("help", HelpState(machine))
    machine.add_state("battle", BattleState(machine))
    machine.add_state("game_over", GameOverState(machine))

    machine.change_state("menu")

    while True:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            machine.handle_event(event)

        # Update
        machine.update()

        # Render
        machine.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
