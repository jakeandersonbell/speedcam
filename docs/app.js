const firebaseConfig = {
    databaseURL: "https://your-project-id.firebaseio.com/",
};

firebase.initializeApp(firebaseConfig);
const db = firebase.database();

// Listen for the latest entries
const logsRef = db.ref('speed_logs').limitToLast(10);

logsRef.on('value', (snapshot) => {
    const data = snapshot.val();
    const listElement = document.getElementById('speed-list');
    listElement.innerHTML = ''; // Clear old list

    const entries = Object.values(data).reverse();
    
    // Update the Big Display
    document.getElementById('latest-speed').innerText = entries[0].speed;

    // Build the list
    entries.forEach(log => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${log.speed} mph</strong> <small>${log.direction}</small> <span>${log.timestamp.split(' ')[1]}</span>`;
        listElement.appendChild(li);
    });
});