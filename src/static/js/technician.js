(() => {
    "use strict";

    const reportForm = document.querySelector("#report-form");
    const photoForm = document.querySelector("#photo-form");
    const picker = document.querySelector("[data-photo-picker]");
    const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
    const dirtyForms = new Set();
    const photos = [];
    let uploadUrl = photoForm?.dataset.uploadUrl;
    let sending = false;
    let reportSaved = false;

    document.querySelectorAll("[data-dirty-form]").forEach(form => {
        form.addEventListener("input", () => dirtyForms.add(form));
    });
    window.addEventListener("beforeunload", event => {
        if (dirtyForms.size || photos.some(photo => photo.state !== "done")) {
            event.preventDefault();
            event.returnValue = "";
        }
    });
    document.querySelectorAll("[data-complete-form], [data-action-form]").forEach(form => {
        form.addEventListener("submit", event => {
            if (form.dataset.completeForm !== undefined &&
                !window.confirm("ซ่อมและทดสอบเรียบร้อยแล้ว ยืนยันปิดงานนี้?")) {
                event.preventDefault();
                return;
            }
            dirtyForms.delete(form);
            form.querySelector("button[type=submit]").disabled = true;
        });
    });

    const humanError = document.querySelector("#id_is_human_error");
    if (humanError) {
        const details = document.querySelector("#human-error-details");
        const updateHumanError = () => {
            details.hidden = !humanError.checked;
            humanError.setAttribute("aria-expanded", String(humanError.checked));
        };
        humanError.addEventListener("change", updateHumanError);
        updateHumanError();
    }

    const categoryPicker = document.querySelector("[data-category-picker]");
    if (categoryPicker) {
        const field = document.querySelector("#id_failure_category");
        const categories = JSON.parse(document.querySelector("#failure-category-tree").textContent);
        const byId = new Map(categories.map(category => [String(category.id), category]));
        const children = new Map();
        categories.forEach(category => {
            const parent = byId.has(String(category.parent_id)) ? String(category.parent_id) : "";
            if (!children.has(parent)) children.set(parent, []);
            children.get(parent).push(category);
        });
        const levels = categoryPicker.querySelector("[data-category-levels]");
        const summary = categoryPicker.querySelector("[data-category-summary]");
        let selectedPath = [];
        let selected = byId.get(field.value);
        const visited = new Set();
        while (selected && !visited.has(String(selected.id))) {
            visited.add(String(selected.id));
            selectedPath.unshift(String(selected.id));
            selected = byId.get(String(selected.parent_id));
        }

        function renderCategories(focusLevel) {
            levels.replaceChildren();
            let parent = "";
            let depth = 0;
            const pathNames = [];
            const seen = new Set();
            while (children.has(parent) && !seen.has(parent)) {
                seen.add(parent);
                const wrapper = document.createElement("div");
                const label = document.createElement("label");
                const select = document.createElement("select");
                select.id = `failure-category-level-${depth}`;
                label.htmlFor = select.id;
                label.textContent = depth === 0 ? "1. เลือกกลุ่มอาการเสีย" : `${depth + 1}. เลือกรายละเอียดเพิ่มเติม`;
                select.append(new Option(depth === 0 ? "ไม่แน่ใจ / ยังไม่ระบุ" : "ยังไม่ทราบรายละเอียดเพิ่มเติม", ""));
                for (const category of children.get(parent)) {
                    select.append(new Option(category.name, String(category.id)));
                }
                select.value = selectedPath[depth] || "";
                const level = depth;
                select.addEventListener("change", () => {
                    selectedPath = selectedPath.slice(0, level);
                    if (select.value) selectedPath.push(select.value);
                    field.value = selectedPath.at(-1) || "";
                    field.dispatchEvent(new Event("input", { bubbles: true }));
                    renderCategories(level);
                });
                wrapper.append(label, select);
                levels.append(wrapper);
                if (!select.value) break;
                pathNames.push(byId.get(select.value).name);
                parent = select.value;
                depth += 1;
            }
            summary.textContent = pathNames.length
                ? `เลือกแล้ว: ${pathNames.join(" → ")}`
                : "ยังไม่ระบุประเภทอาการเสีย";
            if (!categories.length) {
                summary.textContent = "ยังไม่มีประเภทอาการเสียสำหรับเครื่องนี้ สามารถบันทึกซ่อมเสร็จได้";
            }
            if (focusLevel !== undefined) {
                document.getElementById(`failure-category-level-${focusLevel}`)?.focus();
            }
        }

        renderCategories();
        document.querySelector("[data-category-fallback]").hidden = true;
        categoryPicker.hidden = false;
    }

    const machine = document.querySelector("#id_machine");
    if (machine) {
        const search = document.querySelector("#machine-search");
        const choices = Array.from(machine.options);
        const jobs = JSON.parse(document.querySelector("#open-jobs").textContent);
        document.querySelector("[data-machine-search]").hidden = false;
        search.addEventListener("input", () => {
            const query = search.value.trim().toLocaleLowerCase();
            const selected = machine.value;
            const matching = choices.filter(option =>
                !option.value || option.text.toLocaleLowerCase().includes(query)
            );
            machine.replaceChildren(...matching);
            if (!matching.some(option => option.value === selected) && selected) {
                machine.append(choices.find(option => option.value === selected));
            }
            machine.value = selected;
            document.querySelector("#machine-results").textContent =
                query ? `พบ ${matching.filter(option => option.value).length} เครื่อง · เลือกจากรายการด้านล่าง` : "";
        });
        const warnDuplicate = () => {
            const existing = jobs.find(job => job.machine === machine.value);
            document.querySelector("#duplicate-warning").hidden = !existing;
            if (existing) document.querySelector("#duplicate-link").href = existing.url;
        };
        machine.addEventListener("change", warnDuplicate);
        warnDuplicate();
    }

    const flattenErrors = errors => Object.values(errors).flat().join(" · ");

    async function compressPhoto(photo) {
        const image = new Image();
        await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = () => reject(new Error("เปิดรูปนี้ไม่ได้ กรุณาใช้รูป JPG หรือ PNG"));
            image.src = photo.preview;
        });
        const scale = Math.min(1, 1600 / Math.max(image.naturalWidth, image.naturalHeight));
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
        const context = canvas.getContext("2d");
        context.fillStyle = "#fff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        return new Promise((resolve, reject) => {
            canvas.toBlob(blob => {
                if (blob) resolve(blob);
                else reject(new Error("เตรียมรูปไม่สำเร็จ กรุณาเลือกรูปใหม่"));
            }, "image/jpeg", 0.82);
        });
    }

    function sendPhoto(blob, photo) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("POST", uploadUrl);
            xhr.setRequestHeader("X-CSRFToken", csrf);
            xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
            xhr.timeout = 60000;
            xhr.upload.onprogress = event => {
                if (event.lengthComputable) {
                    photo.status.textContent = `กำลังส่งรูป ${Math.round(event.loaded / event.total * 100)}%`;
                }
            };
            xhr.onerror = xhr.ontimeout = () =>
                reject(new Error("ส่งรูปไม่สำเร็จ ตรวจสอบอินเทอร์เน็ต แล้วกดลองอีกครั้ง"));
            xhr.onload = () => {
                let result;
                try {
                    result = JSON.parse(xhr.responseText);
                } catch {
                    reject(new Error("ส่งรูปไม่ได้ กรุณาเปิดงานใหม่เพื่อตรวจสอบการเข้าสู่ระบบ"));
                    return;
                }
                if (xhr.status === 201) resolve(result);
                else reject(new Error(result.errors ? flattenErrors(result.errors) : "ส่งรูปไม่สำเร็จ กรุณาลองอีกครั้ง"));
            };
            const data = new FormData();
            data.append("image", blob, "repair.jpg");
            xhr.send(data);
        });
    }

    function updatePhotoFeedback() {
        const feedback = document.querySelector("[data-photo-feedback]");
        if (feedback && photos.length) {
            feedback.textContent = photos.every(photo => photo.state === "done")
                ? "ส่งรูปครบแล้ว ✓" : "งานซ่อมถูกบันทึกแล้ว รูปที่ยังไม่สำเร็จกด «ลองส่งอีกครั้ง» ได้";
        }
    }

    async function uploadOne(photo) {
        if (!uploadUrl || photo.state === "done" || photo.state === "sending") return;
        photo.state = "sending";
        photo.retry.hidden = true;
        photo.remove.disabled = true;
        photo.status.textContent = "กำลังเตรียมรูป…";
        try {
            const blob = await compressPhoto(photo);
            await sendPhoto(blob, photo);
            photo.state = "done";
            photo.status.textContent = "บันทึกรูปแล้ว ✓";
            photo.remove.hidden = true;
        } catch (error) {
            photo.state = "failed";
            photo.status.textContent = error.message;
            photo.retry.hidden = false;
            photo.remove.disabled = false;
        }
        updatePhotoFeedback();
    }

    async function uploadPending() {
        if (sending) return;
        sending = true;
        const button = document.querySelector("[data-upload-button]");
        if (button) button.disabled = true;
        for (const photo of photos) await uploadOne(photo);
        sending = false;
        if (button) button.disabled = false;
        updatePhotoFeedback();
    }

    if (picker) {
        picker.hidden = false;
        const camera = picker.querySelector("[data-camera]");
        const gallery = picker.querySelector("[data-gallery]");
        picker.querySelector("[data-camera-button]").addEventListener("click", () => camera.click());
        picker.querySelector("[data-gallery-button]").addEventListener("click", () => gallery.click());
        const addPhotos = event => {
            picker.querySelector("[data-photo-feedback]").textContent = "";
            for (const file of event.target.files) {
                if (file.size > 25 * 1024 * 1024) {
                    picker.querySelector("[data-photo-feedback]").textContent = "บางรูปใหญ่เกิน 25 MB กรุณาเลือกรูปขนาดเล็กลง";
                    continue;
                }
                const photo = { preview: URL.createObjectURL(file), state: "pending" };
                const item = document.createElement("div");
                item.className = "photo-item";
                const image = document.createElement("img");
                image.src = photo.preview;
                image.alt = "รูปที่เลือกสำหรับงานซ่อม";
                photo.status = document.createElement("p");
                photo.status.textContent = "รอส่งรูป";
                photo.retry = document.createElement("button");
                photo.retry.type = "button";
                photo.retry.textContent = "ลองส่งอีกครั้ง";
                photo.retry.hidden = true;
                photo.retry.addEventListener("click", () => uploadOne(photo));
                photo.remove = document.createElement("button");
                photo.remove.type = "button";
                photo.remove.textContent = "เอารูปนี้ออก";
                photo.remove.addEventListener("click", () => {
                    photos.splice(photos.indexOf(photo), 1);
                    URL.revokeObjectURL(photo.preview);
                    item.remove();
                });
                item.append(image, photo.status, photo.retry, photo.remove);
                picker.querySelector("[data-photo-list]").append(item);
                photos.push(photo);
            }
            event.target.value = "";
            if (reportSaved) uploadPending();
        };
        camera.addEventListener("change", addPhotos);
        gallery.addEventListener("change", addPhotos);
    }

    if (photoForm) {
        const button = photoForm.querySelector("[data-upload-button]");
        button.hidden = false;
        photoForm.addEventListener("submit", event => {
            event.preventDefault();
            if (!photos.length) {
                picker.querySelector("[data-photo-feedback]").textContent = "กรุณาถ่ายรูปหรือเลือกรูปก่อน";
                return;
            }
            uploadPending();
        });
    }

    if (reportForm) {
        reportForm.addEventListener("submit", async event => {
            event.preventDefault();
            if (reportSaved) return;
            const button = document.querySelector("#save-report");
            const feedback = document.querySelector("#form-feedback");
            if (button.disabled) return;
            button.disabled = true;
            button.textContent = "กำลังบันทึกงาน…";
            feedback.hidden = true;
            try {
                const response = await fetch(reportForm.action || window.location.href, {
                    method: "POST",
                    headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf },
                    body: new FormData(reportForm),
                });
                const result = await response.json();
                if (!response.ok) throw new Error(
                    result.errors ? flattenErrors(result.errors) : "บันทึกไม่ได้ กรุณาลองอีกครั้ง"
                );
                reportSaved = true;
                dirtyForms.delete(reportForm);
                uploadUrl = result.upload_url;
                document.querySelector("#report-fields").disabled = true;
                button.hidden = true;
                const link = document.querySelector("#saved-job-link");
                link.href = result.url;
                link.textContent = `เปิดงาน #${result.job_id} →`;
                document.querySelector("#saved-panel").hidden = false;
                if (!photos.length) {
                    window.location.assign(result.url);
                    return;
                }
                await uploadPending();
                document.querySelector("#saved-panel").scrollIntoView({ behavior: "smooth" });
            } catch (error) {
                feedback.textContent = error instanceof SyntaxError
                    ? "ติดต่อระบบไม่ได้ กรุณาเปิดรายการงานเพื่อตรวจสอบก่อนแจ้งซ้ำ"
                    : error.message;
                if (error instanceof TypeError) {
                    feedback.textContent = "การเชื่อมต่อขัดข้อง ข้อมูลยังอยู่ในหน้านี้ กรุณาตรวจสอบรายการงานก่อนแจ้งซ้ำ";
                }
                feedback.hidden = false;
                feedback.focus();
            } finally {
                button.disabled = false;
                button.textContent = "บันทึกแจ้งซ่อม";
            }
        });
    }
})();
