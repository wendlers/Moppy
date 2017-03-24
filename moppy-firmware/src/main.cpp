#include <TimerOne.h>

//First pin being used for floppies, and the last pin.  Used for looping over all pins.
const byte FIRST_PIN = 2;
const byte PIN_MAX = 17;

const unsigned long RESOLUTION = 40; //Microsecond resolution for notes

/*NOTE: Many of the arrays below contain unused indexes.  This is
 to prevent the Arduino from having to convert a pin input to an alternate
 array index and save as many cycles as possible.  In other words information
 for pin 2 will be stored in index 2, and information for pin 4 will be
 stored in index 4.*/

/*An array of maximum track positions for each step-control pin.  Even pins
 are used for control, so only even numbers need a value here.  3.5" Floppies have
 80 tracks, 5.25" have 50.  These should be doubled, because each tick is now
 half a position (use 158 and 98).
 */
byte MAX_POSITION[] =
{
    0, 0, 158, 0, 158, 0, 158, 0, 158, 0, 158, 0, 158, 0, 158, 0, 158, 0
};

//Array to track the current position of each floppy head.  (Only even indexes (i.e. 2,4,6...) are used)
byte currentPosition[] =
{
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

/*Array to keep track of state of each pin.  Even indexes track the control-pins for toggle purposes.  Odd indexes
 track direction-pins.  LOW = forward, HIGH=reverse
 */
int currentState[] =
{
    0, 0, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW
};

//Current period assigned to each pin.  0 = off.  Each period is of the length specified by the RESOLUTION
//variable above.  i.e. A period of 10 is (RESOLUTION x 10) microseconds long.
unsigned int currentPeriod[] =
{
    0, 0 , 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

//Current tick
unsigned int currentTick[] =
{
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};

void tick();
void togglePin(byte pin, byte direction_pin);
void reset();

//Setup pins (Even-odd pairs for step control and direction
void setup()
{
    pinMode( 2, OUTPUT); // Step control 	1
    pinMode( 3, OUTPUT); // Direction 		1
    pinMode( 4, OUTPUT); // Step control 	2
    pinMode( 5, OUTPUT); // Direction 		2
    pinMode( 6, OUTPUT); // Step control 	3
    pinMode( 7, OUTPUT); // Direction 		3
    pinMode( 8, OUTPUT); // Step control 	4
    pinMode( 9, OUTPUT); // Direction 		4
    pinMode(10, OUTPUT); // Step control 	5
    pinMode(11, OUTPUT); // Direction 		5
    pinMode(12, OUTPUT); // Step control 	6
    pinMode(13, OUTPUT); // Direction 		6
    pinMode(14, OUTPUT); // Step control 	7
    pinMode(15, OUTPUT); // Direction 		7
    pinMode(16, OUTPUT); // Step control 	8
    pinMode(17, OUTPUT); // Direction 		8

    // With all pins setup, let's do a first run reset
    reset();
    delay(1000);

    Timer1.initialize(RESOLUTION); 	// Set up a timer at the defined resolution
    Timer1.attachInterrupt(tick); 	// Attach the tick function

    Serial.begin(9600);
}

void loop()
{
    //Only read if we have 3 bytes waiting
    if(Serial.available() > 2)
    {
        // Watch for special 100-message to act on
        if (Serial.peek() == 100)
        {
            // Clear the peeked 100 byte so we can get the following data packet
            Serial.read();
            byte b = Serial.read();

            switch(b)
            {
            case 1:
            case 2:
            case 3:
            case 4:
                break;
            default:
                reset();
                break;
            }
            // Flush any remaining messages.
            while(Serial.available() > 0)
            {
                Serial.read();
            }
        }
        else
        {
            currentPeriod[Serial.read()] = (Serial.read() << 8) | Serial.read();
        }
    }
}

/*
Called by the timer interrupt at the specified resolution.
 */
void tick()
{
    /*
     If there is a period set for control pin 2, count the number of
     ticks that pass, and toggle the pin if the current period is reached.
     */
    if (currentPeriod[2]>0)
    {
        currentTick[2]++;
        if (currentTick[2] >= currentPeriod[2])
        {
            togglePin(2,3);
            currentTick[2]=0;
        }
    }
    if (currentPeriod[4]>0)
    {
        currentTick[4]++;
        if (currentTick[4] >= currentPeriod[4])
        {
            togglePin(4,5);
            currentTick[4]=0;
        }
    }
    if (currentPeriod[6]>0)
    {
        currentTick[6]++;
        if (currentTick[6] >= currentPeriod[6])
        {
            togglePin(6,7);
            currentTick[6]=0;
        }
    }
    if (currentPeriod[8]>0)
    {
        currentTick[8]++;
        if (currentTick[8] >= currentPeriod[8])
        {
            togglePin(8,9);
            currentTick[8]=0;
        }
    }
    if (currentPeriod[10]>0)
    {
        currentTick[10]++;
        if (currentTick[10] >= currentPeriod[10])
        {
            togglePin(10,11);
            currentTick[10]=0;
        }
    }
    if (currentPeriod[12]>0)
    {
        currentTick[12]++;
        if (currentTick[12] >= currentPeriod[12])
        {
            togglePin(12,13);
            currentTick[12]=0;
        }
    }
    if (currentPeriod[14]>0)
    {
        currentTick[14]++;
        if (currentTick[14] >= currentPeriod[14])
        {
            togglePin(14,15);
            currentTick[14]=0;
        }
    }
    if (currentPeriod[16]>0)
    {
        currentTick[16]++;
        if (currentTick[16] >= currentPeriod[16])
        {
            togglePin(16,17);
            currentTick[16]=0;
        }
    }

}

void togglePin(byte pin, byte direction_pin)
{
    // Switch directions if end has been reached
    if (currentPosition[pin] >= MAX_POSITION[pin])
    {
        currentState[direction_pin] = HIGH;
        digitalWrite(direction_pin,HIGH);
    }
    else if (currentPosition[pin] <= 0)
    {
        currentState[direction_pin] = LOW;
        digitalWrite(direction_pin,LOW);
    }

    // Update currentPosition
    if (currentState[direction_pin] == HIGH)
    {
        currentPosition[pin]--;
    }
    else
    {
        currentPosition[pin]++;
    }

    // Pulse the control pin
    digitalWrite(pin,currentState[pin]);
    currentState[pin] = ~currentState[pin];
}

//Resets all the pins
void reset()
{
    // Stop all notes (don't want to be playing during/after reset)
    for (byte p=FIRST_PIN; p<=PIN_MAX; p+=2)
    {
        currentPeriod[p] = 0; // Stop playing notes
    }

    // New all-at-once reset
    for (byte s=0; s<80; s++)   // For max drive's position
    {
        for (byte p=FIRST_PIN; p<=PIN_MAX; p+=2)
        {
            digitalWrite(p+1,HIGH); // Go in reverse
            digitalWrite(p,HIGH);
            digitalWrite(p,LOW);
        }
        delay(5);
    }

    for (byte p=FIRST_PIN; p<=PIN_MAX; p+=2)
    {
        currentPosition[p] = 0; // We're reset.
        digitalWrite(p+1,LOW);
        currentState[p+1] = 0; // Ready to go forward.
    }
}
