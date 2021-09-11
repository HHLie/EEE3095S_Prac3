# Import libraries
import RPi.GPIO as GPIO
import random
import ES2EEPROMUtils
import os
import time

# some global variables that need to change as we run the program
end_of_game = None  # set if the user wins or ends the game

# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy = 32
btn_submit = 16
btn_increase = 18
buzzer = 33
eeprom = ES2EEPROMUtils.ES2EEPROM()
pwm_LED = None
pwm_buzzer = None
Guess_value = 0
Guess_count = 0
value = None



# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


# Print the game menu
def menu():
    global end_of_game, Guess_value, value, Guess_count
    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
    elif option == "P":
        os.system('clear')
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        end_of_game = False
        Guess_count = 0
        Guess_value = 0
        value = generate_number()
        while not end_of_game:
            pass
    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    # print the scores to the screen in the expected format
    print("There are {} scores. Here are the top 3!".format(count))
    # print out the scores in the required format
    for index, score in enumerate(raw_data[0:3]):
        print("{} - {} took {} guesses.".format(index+1,score[0],score[1]))
    pass


# Setup Pins
def setup():
    global pwm_LED,pwm_buzzer, Guess_value
    # Setup board mode
    GPIO.setmode(GPIO.BOARD)
    # Setup regular GPIO
    #LEDS 
    for pin in LED_value:
        GPIO.setup(pin,GPIO.OUT)
        GPIO.output(pin,GPIO.LOW)
    
    #buttons
    GPIO.setup(btn_submit , GPIO.IN , pull_up_down = GPIO.PUD_UP)
    GPIO.setup(btn_increase , GPIO.IN , pull_up_down = GPIO.PUD_UP)

    # Setup PWM channels
    GPIO.setup(LED_accuracy,GPIO.OUT)
    GPIO.setup(buzzer,GPIO.OUT)
    #setup for LED_accuracy
    pwm_LED = GPIO.PWM(LED_accuracy, 1000)
    pwm_LED.start(0)
    #setup for the buzzer
    pwm_buzzer = GPIO.PWM(buzzer, 1000)
    pwm_buzzer.start(0)

    # Setup debouncing and callbacks
    GPIO.add_event_detect(btn_submit, GPIO.FALLING, callback = btn_guess_pressed, bouncetime=200)
    GPIO.add_event_detect(btn_increase, GPIO.FALLING, callback = btn_increase_pressed, bouncetime=200)
    pass


# Load high scores
def fetch_scores():
    # get however many scores there are
    score_count = eeprom.read_byte(0)
    # Get the scores
    score_data = eeprom.read_block(1, 4*score_count)
    # convert the codes back to ascii
    scores = []
    length = len(score_data)
    for i in range((int)(length/4)):
        str_temp = ""
        for j in range(3):
            str_temp += chr(score_data[4*i+j])
        scores.append([str_temp,score_data[4*i+3]])
    # return back the results
    return score_count, scores


# Save high scores
def save_scores(name, guesses):
    # fetch scores
    count, s = fetch_scores()
    # include new score
    s.append([name,guesses])
    # sort
    s.sort(key=lambda x: x[1])
    # update total amount of scores
    eeprom.write_block(0, [count+1])
    # write updated scores to EEPROM
    for i, score in enumerate(s):
            data_to_write = []
            for letter in score[0]:
                data_to_write.append(ord(letter))
            data_to_write.append(score[1])
            eeprom.write_block(i+1, data_to_write)
    pass


# Generate guess number
def generate_number():
    return random.randint(0, pow(2, 3)-1)


# Increase button pressed
def btn_increase_pressed(channel):
    global Guess_value
    time.sleep(0.1)
    #increment by 1
    Guess_value += 1
    #convert to binary
    temp_list = list(reversed(str(bin(Guess_value))[2:]))
    missing = 3 - len(temp_list)
    #fill in 0 in gaps to make 3 digit binary
    for i in range(missing):
        temp_list.append('0')
    temp_list = list(reversed(temp_list))

    #Show LED in binary
    for pin in range(3):
        if temp_list[pin] == '1':
            GPIO.output(LED_value[pin],GPIO.HIGH)
        else:
            GPIO.output(LED_value[pin],GPIO.LOW)
    pass


# Guess button
def btn_guess_pressed(channel):
    global one, end_of_game, Guess_value, value, Guess_count
    time.sleep(0.1) # wait
    while GPIO.input(channel) == GPIO.LOW:
        time.sleep(0.5) # wait for hold
        # If they've pressed and held the button, clear up the GPIO and take them back to 
        #the menu screen
        if GPIO.input(channel) == GPIO.LOW:
            print("hold")
            os.system('clear')
            # Disable LEDs and Buzzer
            reset_func()
            end_of_game = True
            break
        # Else process the guess
        # Compare the actual value with the user value displayed on the LEDs
        else:
            # Increment the guess count
            Guess_count += 1
            # if it's an exact guess:
            if Guess_value == value:
                os.system('clear')
                print("You took {} guesses.".format(Guess_count))
                # Disable LEDs and Buzzer
                reset_func()
                # Tell the user and prompt them for a name
                option = input("Enter Your Name:\n")
                # Save score to EEPROM
                save_scores(option,Guess_count)
                end_of_game = True
            # Else do condintionals
            else:
                accuracy_leds()
                trigger_buzzer()
            Guess_value = 0
    pass


# LED Brightness
def accuracy_leds():
    brightness = 0
    #if value is greater than the guess, use guess/value*100 = brightness
    if value > Guess_value:
        brightness = (int)((Guess_value/value)*100)
    #else (8-Guess_value)/(8-value)*100 = brightness
    else:
        brightness = (int)(((8-Guess_value)/(8-value))*100)
    pwm_LED.ChangeDutyCycle(brightness)
    pass

# Sound Buzzer
def trigger_buzzer():
    # Get the absolute difference of the guess and the value 
    buzz = abs(value - Guess_value)
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    if buzz == 1:
        pwm_buzzer.ChangeFrequency(4)  
        pwm_buzzer.ChangeDutyCycle(20)
        pass
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    elif buzz == 2:
        pwm_buzzer.ChangeFrequency(2)  
        pwm_buzzer.ChangeDutyCycle(20)
        pass
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
    elif buzz == 3:
        pwm_buzzer.ChangeFrequency(1)  
        pwm_buzzer.ChangeDutyCycle(20)
        pass
    # Else stop the buzzer if the absolute difference is greater than 3
    else:
        pwm_buzzer.ChangeDutyCycle(0)#stop the buzzer
    pass

# reset function for pwm modules, LEDS
def reset_func():
    global Guess_count, Guess_value
    pwm_LED.ChangeDutyCycle(0) #stop LED_accuracy
    pwm_buzzer.ChangeDutyCycle(0)#stop the buzzer
    for pin in LED_value:
        GPIO.output(pin,GPIO.LOW)
    pass

if __name__ == "__main__":
    try:
        # Call setup function
        setup()
        welcome()
        while True:
            menu()
            pass
    except Exception as e:
        print(e)
    finally:
        pwm_LED.stop() #stop LED_accuracy
        pwm_buzzer.stop()#stop the buzzer
        GPIO.cleanup()
