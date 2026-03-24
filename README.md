# Cloud-Based-Videogame-Recommender-System
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)](https://react.dev/)
[![Shell](https://img.shields.io/badge/Bash-Shell--Scripting-4EAA25?style=flat&logo=gnubash&logoColor=white)](https://react.dev/)

### Overview 
A recommender system is a class of machine learning that uses data to help predict, narrow down, and find what people are looking for among an exponentially growing number of options.
In this project, I developed a cloud-based videogame recommender using a collaborative filtering approach, leveraging user-item interaction patterns to generate personalised game recommendations

### System Design 
The model learns similarities between users and games based on historical interaction data, enabling it to predict future preferences and improve recommendation accuracy over time.

### Deployment & Infrastucture
To provide an interactive user experience, I built a web application using Streamlit, containerised it with Docker, and deployed it on Microsoft Azure Kubernetes Service (AKS). An Ingress-based load balancer distributes incoming traffic across multiple pods, ensuring scalability, high availability, and efficient request handling. The system exposes a stable external endpoint, allowing users to access the application reliably.

### Goal & Future Improvements
The system is designed to enhance user engagement and game discovery through personalised recommendations. Future improvements include integrating real-time (online) recommendation algorithms and extending the system to support additional domains such as music and e-commerce.

## Architecture 

## Interaction of the various components 


## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---
<div align="center"> Made with ❤️ by Jeduthun Idemudia </div>
