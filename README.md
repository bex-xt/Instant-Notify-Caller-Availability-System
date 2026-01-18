#Overview

Instant Notify is a hybrid Client–Server and Peer-to-Peer (P2P) voice communication system designed to solve a common issue in real-time calling systems. Traditional systems only indicate that a user is busy, forcing callers to repeatedly retry. This project introduces an automated notification mechanism that instantly alerts waiting callers when the receiver becomes available.

#Problem Statement

In synchronous communication systems, callers have no way of knowing when a busy user becomes free. This results in repeated call attempts, wasted time, and missed communication opportunities. The project addresses this inefficiency by providing instant availability notifications.

#Solution

The system uses a centralized TCP server to handle user registration, call signaling, and availability tracking. When a user is busy, callers are placed in a waiting queue. As soon as the user becomes free, the server automatically notifies the waiting caller. After call acceptance, communication switches to direct P2P audio streaming using UDP for low latency.

#Architecture

Central Server (TCP):
Handles user registration, call requests, availability status, and notifications.

Peer-to-Peer Layer (UDP):
Manages real-time audio transmission directly between clients to reduce latency and server load.

#Features

Instant notification when a busy user becomes available

Hybrid Client–Server and P2P architecture

Low-latency real-time voice communication

Waiting list management for callers

Command-line interface for call control

#Commands (CLI)

call <username> – Initiate a call

accept – Accept an incoming call

reject – Reject an incoming call

hangup – End the current call

who – View all registered users

#Technologies Used

Python

Socket Programming

TCP/IP and UDP

Multithreading

Audio Streaming (PortAudio / sounddevice)

#Project Status

The project is fully functional with a CLI-based interface and supports real-time audio communication and instant availability notifications.

#Future Enhancements

Graphical User Interface (GUI)

Missed call and call-attempt notifications

Audio alert/ringtone for availability notification

Improved security and scalability

Enhanced multi-user handling

#Academic Context

This project was developed as part of the Basic Concepts in Computer Networks (PBCCT304) course during Semester S3.
