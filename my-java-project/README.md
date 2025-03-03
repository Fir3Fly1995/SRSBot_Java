# My Java Project

This is a simple Java project that demonstrates the structure of a Maven-based application.

## Project Structure

```
my-java-project
├── src
│   ├── main
│   │   ├── java
│   │   │   └── App.java
│   │   └── resources
│   ├── test
│   │   ├── java
│   │   │   └── AppTest.java
│   │   └── resources
├── pom.xml
└── README.md
```

## Requirements

- Java Development Kit (JDK) 11 or higher
- Apache Maven

## Building the Project

To build the project, navigate to the project directory and run the following command:

```
mvn clean install
```

## Running the Application

After building the project, you can run the application using the following command:

```
mvn exec:java -Dexec.mainClass="App"
```

## Running Tests

To run the tests, use the following command:

```
mvn test
```

## License

This project is licensed under the MIT License.