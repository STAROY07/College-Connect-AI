// College Connect AI — Full Admin CMS

const SCHEMA = {
  updates: {
    title: "Updates & Announcements",
    key: "updates",
    fields: [
      { id: "title", label: "Title", type: "text", required: true },
      { id: "category", label: "Category", type: "select", options: ["General Update", "Exam Notice", "Portals / Results", "Admission Notice", "Scholarship Notice"], required: true },
      { id: "content", label: "Content", type: "textarea", required: true },
      { id: "source", label: "Source", type: "text", default: "College Office" },
      { id: "url", label: "Optional URL", type: "text" },
      { id: "status", label: "Status", type: "select", options: ["Active", "Archived"], default: "Active" }
    ],
    tableCols: ["Title", "Category", "Date", "Status"]
  },
  faqs: {
    title: "Frequently Asked Questions",
    key: "faqs",
    fields: [
      { id: "question", label: "Question", type: "text", required: true },
      { id: "category", label: "Category", type: "text", required: true },
      { id: "answer", label: "Answer", type: "textarea", required: true }
    ],
    tableCols: ["Question", "Category"]
  },
  programmes: {
    title: "Undergraduate Programmes",
    key: "ug_programmes", // Only editing UG for simplicity in UI, can be expanded.
    fields: [
      { id: "id", label: "Program ID", type: "text", required: true },
      { id: "name", label: "Program Name", type: "text", required: true },
      { id: "duration", label: "Duration", type: "text", default: "3 Years" },
      { id: "eligibility", label: "Eligibility", type: "textarea" },
      { id: "seats", label: "Total Seats", type: "text" },
      { id: "specializations", label: "Specializations (Comma separated)", type: "text" },
      { id: "description", label: "Description", type: "textarea" }
    ],
    tableCols: ["Program Name", "Duration", "Seats"]
  },
  services: {
    title: "Student Extension Services",
    key: "services",
    fields: [
      { id: "name", label: "Service Name", type: "text", required: true },
      { id: "description", label: "Description", type: "textarea", required: true },
      { id: "time_minutes", label: "Processing Time (Mins)", type: "text" },
      { id: "location", label: "Location", type: "text" }
    ],
    tableCols: ["Service Name", "Processing Time", "Location"]
  },
  welfare: {
    title: "Welfare & Scholarships",
    key: "schemes",
    fields: [
      { id: "name", label: "Scheme Name", type: "text", required: true },
      { id: "description", label: "Description", type: "textarea", required: true },
      { id: "eligibility", label: "Eligibility Criteria", type: "textarea" },
      { id: "amount", label: "Amount / Benefit", type: "text" }
    ],
    tableCols: ["Scheme Name", "Amount"]
  },
  kaushal: {
    title: "Kaushal Centre Courses",
    key: "courses",
    fields: [
      { id: "name", label: "Course Name", type: "text", required: true },
      { id: "category", label: "Category", type: "text" }
    ],
    tableCols: ["Course Name", "Category"]
  },
  admissions: {
    title: "Admissions Information",
    key: "notices",
    fields: [
      { id: "title", label: "Notice Title", type: "text", required: true },
      { id: "content", label: "Notice Details", type: "textarea", required: true }
    ],
    tableCols: ["Notice Title", "Details"]
  },
  rules: {
    title: "Rules & Code of Conduct",
    key: "discipline_and_code_of_conduct",
    fields: [
      { id: "rule", label: "Rule text", type: "textarea", required: true }
    ],
    tableCols: ["Rule Text"]
  }
};

let currentSection = "updates";
let currentData = null; // Holds the entire JSON file data
let editIndex = -1; // -1 means new item

document.addEventListener('DOMContentLoaded', () => {
  // Sidebar navigation
  document.querySelectorAll('#admin-nav button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#admin-nav button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSection = btn.dataset.section;
      loadSection(currentSection);
    });
  });

  // Load initial section
  loadSection(currentSection);

  // Form submission
  document.getElementById('dynamic-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    await saveForm();
  });
});

// ─── Modal Helpers ──────────────────────────────────────────────
window.openDynamicModal = (idx = -1) => {
  editIndex = idx;
  const s = SCHEMA[currentSection];
  document.getElementById('modal-title').textContent = idx === -1 ? `Add New ${s.title.split(' ')[0]}` : `Edit ${s.title.split(' ')[0]}`;
  
  const container = document.getElementById('dynamic-form-fields');
  container.innerHTML = ''; // clear

  const isStringArray = (currentSection === 'rules');

  let item = null;
  if (idx !== -1) {
      const arr = currentData[s.key] || [];
      item = arr[idx];
  }

  s.fields.forEach(f => {
    const group = document.createElement('div');
    group.className = 'form-group';
    group.style.marginBottom = '15px';

    const label = document.createElement('label');
    label.textContent = f.label + (f.required ? ' *' : '');
    label.style.display = 'block';
    label.style.marginBottom = '5px';
    label.style.fontSize = '12px';
    label.style.fontWeight = '600';

    let input;
    if (f.type === 'textarea') {
      input = document.createElement('textarea');
      input.className = 'form-control';
      input.style.minHeight = '80px';
    } else if (f.type === 'select') {
      input = document.createElement('select');
      input.className = 'form-control';
      f.options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        input.appendChild(option);
      });
    } else {
      input = document.createElement('input');
      input.type = f.type;
      input.className = 'form-control';
    }

    input.id = `fld-${f.id}`;
    if (f.required) input.required = true;

    // Pre-fill
    if (item) {
        if (isStringArray && f.id === 'rule') {
            input.value = item;
        } else {
            let val = item[f.id] || '';
            if (f.id === 'specializations' && Array.isArray(val)) {
                val = val.join(', ');
            }
            input.value = val;
        }
    } else if (f.default) {
        input.value = f.default;
    }

    group.appendChild(label);
    group.appendChild(input);
    container.appendChild(group);
  });

  document.getElementById('modal-dynamic-form').classList.add('open');
};

window.closeModal = id => {
  document.getElementById(id).classList.remove('open');
};

// ─── Data Operations ─────────────────────────────────────────────

async function loadSection(sec) {
  const s = SCHEMA[sec];
  document.getElementById('section-title').textContent = s.title;
  const container = document.getElementById('table-container');
  container.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">Loading data...</div>';

  try {
    const res = await fetch(`/admin/api/data/${sec}`);
    const result = await res.json();
    if (result.success) {
      currentData = result.data;
      renderTable(sec, currentData);
    } else {
      container.innerHTML = `<div style="padding: 20px; color: red;">Error: ${result.message}</div>`;
    }
  } catch (err) {
    container.innerHTML = `<div style="padding: 20px; color: red;">Network error while loading data.</div>`;
  }
}

function renderTable(sec, data) {
  const s = SCHEMA[sec];
  let arr = data[s.key] || [];
  if (!Array.isArray(arr)) arr = []; // Fallback

  if (arr.length === 0) {
    document.getElementById('table-container').innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);">No records found. Click "+ Add New Item" to create one.</div>';
    return;
  }

  const isStringArray = (sec === 'rules');

  let html = `<table class="dynamic-table">
    <thead><tr>`;
  
  s.tableCols.forEach(col => {
    html += `<th>${col}</th>`;
  });
  html += `<th style="text-align: right; width: 120px;">Actions</th></tr></thead><tbody>`;

  arr.forEach((item, idx) => {
    html += `<tr>`;
    if (isStringArray) {
        html += `<td>${(item || '').substring(0, 100)}...</td>`;
    } else {
        // Map fields to table cols generically
        s.tableCols.forEach((col, i) => {
          const fieldId = s.fields[i].id; // assuming first N fields match tableCols order loosely
          let val = item[fieldId] || '-';
          if (val.length > 80) val = val.substring(0, 80) + '...';
          html += `<td>${val}</td>`;
        });
    }

    html += `<td style="text-align: right;">
        <button class="btn" style="background: transparent; color: var(--primary); padding: 4px 8px; font-size: 12px; margin-right: 5px;" onclick="openDynamicModal(${idx})">Edit</button>
        <button class="btn" style="background: transparent; color: var(--danger); padding: 4px 8px; font-size: 12px;" onclick="deleteItem(${idx})">Delete</button>
      </td>
    </tr>`;
  });

  html += `</tbody></table>`;
  document.getElementById('table-container').innerHTML = html;
}

async function saveForm() {
  const s = SCHEMA[currentSection];
  const isStringArray = (currentSection === 'rules');
  
  // Construct object from form
  let newItem = isStringArray ? '' : {};
  
  s.fields.forEach(f => {
    const val = document.getElementById(`fld-${f.id}`).value.trim();
    if (isStringArray) {
        newItem = val;
    } else {
        if (f.id === 'specializations') {
            newItem[f.id] = val.split(',').map(v => v.trim()).filter(v => v);
        } else {
            newItem[f.id] = val;
        }
    }
  });

  if (!isStringArray && !newItem.id && currentSection !== 'faqs' && currentSection !== 'updates') {
      newItem.id = `item_${Date.now()}`;
  }
  
  if (currentSection === 'updates' && !newItem.id) newItem.id = `upd_${Date.now()}`;
  if (currentSection === 'faqs' && !newItem.id) newItem.id = `faq_${Date.now()}`;
  if (currentSection === 'updates') {
      newItem.date_added = newItem.date_added || new Date().toISOString().split('T')[0];
      newItem.last_updated = new Date().toISOString().split('T')[0];
  }

  // Inject into JSON
  if (!currentData[s.key]) currentData[s.key] = [];
  
  if (editIndex === -1) {
    if (currentSection === 'updates') {
        currentData[s.key].unshift(newItem);
    } else {
        currentData[s.key].push(newItem);
    }
  } else {
    // Retain existing fields not in schema
    if (!isStringArray) {
        newItem = { ...currentData[s.key][editIndex], ...newItem };
    }
    currentData[s.key][editIndex] = newItem;
  }

  await persistData();
  closeModal('modal-dynamic-form');
}

window.deleteItem = async (idx) => {
  if (!confirm("Are you sure you want to delete this item? It will be removed from the public portal and AI assistant immediately.")) return;
  
  const s = SCHEMA[currentSection];
  currentData[s.key].splice(idx, 1);
  await persistData();
}

async function persistData() {
  const btn = document.getElementById('btn-add-new');
  btn.disabled = true;
  btn.textContent = "Saving...";

  try {
    const res = await fetch(`/admin/api/data/${currentSection}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentData)
    });
    const result = await res.json();
    if (result.success) {
      alert("Changes saved and synced!");
      renderTable(currentSection, currentData);
    } else {
      alert("Error saving: " + result.message);
    }
  } catch (err) {
    alert("Network error.");
  } finally {
    btn.disabled = false;
    btn.textContent = "+ Add New Item";
  }
}
