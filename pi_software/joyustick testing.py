import time
import pygame

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise Exception("No controller detected!")

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Sending commands from: {joystick.get_name()}")


while True:
    pygame.event.pump()
    axes = [round(joystick.get_axis(i),2) for i in range(joystick.get_numaxes())]
    print(f"Axes: {axes}")

    print(f"Buttons: {[joystick.get_button(i) for i in range(joystick.get_numbuttons())]}")
    print("-" * 30)
    time.sleep(0.05)
    print(f"power level: {joystick.get_power_level()}")




# 125 mm bottom shaft to shaft arm length
# 145 mm middle shaft to shaft arm length
# 38.6 mm top shaft to tool length