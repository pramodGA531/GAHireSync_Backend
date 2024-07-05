module.exports = {
  apps: [
    {
      name: "RMS_BACKEND",
      script: "gunicorn",
      args: "--bind 0.0.0.0:8001 User_Authentication.wsgi:application",
      interpreter: "python3",
      exec_mode: "fork", // Or "cluster" if you want to run in cluster mode
      instances: 1, // Change to the number of instances you need, or use "max" to run as many instances as available CPUs
      autorestart: true,
      watch: false,
      max_memory_restart: "1G", // Optional: restart if the process uses more than 1GB of memory
      env: {
        NODE_ENV: "production"
      }
    }
  ]
};
