import streamlit as st
import fitz  # PyMuPDF
import cv2
import numpy as np
import pandas as pd
from PIL import Image
from streamlit_cropper import st_cropper
import json

st.set_page_config(page_title="OMR 자동 채점 (박스 지정형)", layout="wide")

if 'boxes' not in st.session_state:
    st.session_state.boxes = []

st.title("📝 OMR 자동 채점 프로그램 v11 (수학 단답형 오답 직관성 강화)")

tab1, tab2 = st.tabs(["🛠️ 1단계: OMR 영역 설정 (설정 저장/불러오기)", "🚀 2단계: 실전 채점 (Grading)"])

def get_grid_absolute(x1, y1, x2, y2, rows, cols):
    cell_w = (x2 - x1) / cols
    cell_h = (y2 - y1) / rows
    
    cells = []
    for r in range(rows):
        row_cells = []
        for c in range(cols):
            left = int(x1 + c * cell_w)
            top = int(y1 + r * cell_h)
            right = int(x1 + (c + 1) * cell_w)
            bottom = int(y1 + (r + 1) * cell_h)
            
            mx = int((right - left) * 0.25)
            my = int((bottom - top) * 0.25)
            row_cells.append({
                'outer': (left, top, right, bottom),
                'inner': (left + mx, top + my, right - mx, bottom - my)
            })
        cells.append(row_cells)
    return cells

def pdf_to_image(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=150)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img

with tab1:
    st.markdown("마우스 드래그로 영역을 잡고, 설정된 OMR 박스 규격을 저장하거나 불러올 수 있습니다.")
    sample_file = st.file_uploader("영점 조절용 스캔본 1장 업로드 (PDF)", type=['pdf'])
    
    if sample_file:
        img = pdf_to_image(sample_file.read())
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("💾 1. OMR 설정 관리")
            uploaded_config = st.file_uploader("📂 기존 설정 파일(.json) 불러오기", type=['json'])
            if uploaded_config:
                if st.button("설정 적용하기"):
                    st.session_state.boxes = json.load(uploaded_config)
                    st.success("설정이 성공적으로 적용되었습니다!")
                    st.rerun()
                    
            if st.session_state.boxes:
                config_json = json.dumps(st.session_state.boxes)
                st.download_button("📥 현재 설정 저장하기 (.json)", data=config_json, file_name="omr_config.json", mime="application/json")
            
            st.write("---")
            st.subheader("➕ 2. 새로 추가할 박스 속성")
            box_type = st.radio("박스 유형", ["객관식 문항", "수험번호", "수학 단답형 (1문항)"], horizontal=True)
            
            if box_type == "객관식 문항":
                start_q = st.number_input("이 박스의 시작 문항 번호", min_value=1, value=1)
                rows = st.number_input("세로 칸 수 (문항 수)", min_value=1, value=20)
                cols = st.number_input("가로 칸 수 (보기 개수)", min_value=1, value=5)
            elif box_type == "수험번호":
                start_q = 0
                rows = st.number_input("세로 칸 수 (숫자 0~9)", min_value=1, value=10)
                cols = st.number_input("가로 칸 수 (수험번호 9칸)", min_value=1, value=9)
            else: # 수학 단답형
                start_q = st.number_input("이 박스의 문항 번호", min_value=1, value=16)
                rows = 10
                cols = 3
                st.info("💡 수학 단답형은 정확도를 위해 **1개 문항씩 개별 지정(10행 3열)** 하도록 고정되어 있습니다.")
            
            st.write("---")
            st.subheader("📋 3. 박스 저장 및 목록")
            
            if st.button("👉 우측에서 잡은 영역을 목록에 추가", use_container_width=True):
                pass
                
            if st.session_state.boxes:
                for i, b in enumerate(st.session_state.boxes):
                    if b['type'] == '객관식 문항':
                        label = f"문항 {b['start_q']}~{b['start_q']+b['rows']-1}"
                    elif b['type'] == '수학 단답형 (1문항)':
                        label = f"단답형 {b['start_q']}번"
                    else:
                        label = "수험번호"
                        
                    cols_btn = st.columns([3, 1])
                    cols_btn[0].write(f"✅ {label} ({b['rows']}행 {b['cols']}열)")
                    if cols_btn[1].button("삭제", key=f"del_{i}"):
                        st.session_state.boxes.pop(i)
                        st.rerun()

        with col2:
            st.subheader("🔍 마우스 드래그 영역")
            rect = st_cropper(img_pil, realtime_update=True, box_color='blue', aspect_ratio=None, return_type='box')
            
            if st.button("➕ 현재 잡아둔 파란색 영역을 리스트에 추가"):
                new_box = {
                    'type': box_type,
                    'start_q': start_q,
                    'rows': rows,
                    'cols': cols,
                    'rect': rect
                }
                st.session_state.boxes.append(new_box)
                st.rerun()
                
            st.write("---")
            st.subheader("👀 전체 인식 영역 미리보기")
            preview_img = img.copy()
            for b in st.session_state.boxes:
                r = b['rect']
                x1, y1, x2, y2 = r['left'], r['top'], r['left'] + r['width'], r['top'] + r['height']
                grid = get_grid_absolute(x1, y1, x2, y2, b['rows'], b['cols'])
                
                if b['type'] == "객관식 문항":
                    color = (0, 0, 255)
                    label = f"Q{b['start_q']}~{b['start_q']+b['rows']-1}"
                elif b['type'] == "수학 단답형 (1문항)":
                    color = (0, 150, 0)
                    label = f"Q{b['start_q']}"
                else:
                    color = (255, 0, 0)
                    label = "ID"
                
                for r_idx, row in enumerate(grid):
                    for c_idx, cell in enumerate(row):
                        cv2.rectangle(preview_img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), color, 1)
                        cv2.rectangle(preview_img, (cell['inner'][0], cell['inner'][1]), (cell['inner'][2], cell['inner'][3]), (0, 255, 255), 2)
                        
                        if r_idx == 0 and c_idx == 0:
                            cv2.putText(preview_img, label, (cell['outer'][0], cell['outer'][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                            
            st.image(cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB), use_container_width=True)

with tab2:
    if not st.session_state.boxes:
        st.warning("1단계 탭에서 먼저 채점 영역(박스)을 최소 1개 이상 등록하거나 설정 파일을 불러와 주세요.")
    else:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.header("1. 데이터 업로드")
            answer_file = st.file_uploader("정답지 파일 (CSV 또는 엑셀)", type=['csv', 'xlsx', 'xls'], key="ans")
            db_file = st.file_uploader("학생 명부 파일 (CSV 또는 엑셀)", type=['csv', 'xlsx', 'xls'], key="db")
            
            answer_key = {}
            if answer_file is not None:
                if answer_file.name.endswith('.csv'):
                    df_ans = pd.read_csv(answer_file)
                else:
                    df_ans = pd.read_excel(answer_file)
                    
                has_points = '배점' in df_ans.columns
                for index, row in df_ans.iterrows():
                    answer_key[int(row['문항번호'])] = {
                        'answer': int(row['정답']),
                        'point': float(row['배점']) if has_points and not pd.isna(row['배점']) else 1.0
                    }
                st.success(f"정답지 로드 완료! (총 {len(answer_key)}문항)")
                
            teacher_dict = {}
            school_dict = {}
            student_dict = {}
            
            if db_file is not None:
                if db_file.name.endswith('.csv'):
                    df_db = pd.read_csv(db_file)
                else:
                    df_db = pd.read_excel(db_file)
                    
                for idx, row in df_db.iterrows():
                    if '선생님 배정 번호' in df_db.columns and pd.notna(row['선생님 배정 번호']):
                        teacher_dict[str(int(row['선생님 배정 번호'])).zfill(2)] = str(row['선생님 성함'])
                    if '학교와 학년 배정 번호' in df_db.columns and pd.notna(row['학교와 학년 배정 번호']):
                        school_dict[str(int(row['학교와 학년 배정 번호'])).zfill(2)] = str(row['학교와 학년'])
                    if '학생 배정 번호' in df_db.columns and pd.notna(row['학생 배정 번호']):
                        student_dict[str(int(row['학생 배정 번호'])).zfill(2)] = str(row['학생 이름'])
                st.success("학생 명부 DB 로드 완료!")
                
            st.header("2. 스캔본 대량 채점")
            test_files = st.file_uploader("학생 OMR 스캔본 (PDF 다중 선택)", type=['pdf'], accept_multiple_files=True, key="tests")
            
            threshold_val = st.slider("마킹 픽셀 감도", 10, 100, 30, help="낮을수록 연한 연필 마킹도 인식합니다.")

        if st.button("🚀 전체 채점 시작", use_container_width=True) and answer_key and test_files:
            all_results = []
            progress_bar = st.progress(0)
            
            for idx, pdf_file in enumerate(test_files):
                img = pdf_to_image(pdf_file.read())
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
                
                student_info = "미등록"
                student_answers = {}
                
                for b in st.session_state.boxes:
                    r = b['rect']
                    x1, y1, x2, y2 = r['left'], r['top'], r['left'] + r['width'], r['top'] + r['height']
                    grid = get_grid_absolute(x1, y1, x2, y2, b['rows'], b['cols'])
                    
                    if b['type'] == '수험번호':
                        id_marks = []
                        for c_idx in range(b['cols']):
                            col_ratios = []
                            for r_idx in range(b['rows']):
                                cell = grid[r_idx][c_idx]
                                roi = thresh[cell['inner'][1]:cell['inner'][3], cell['inner'][0]:cell['inner'][2]]
                                black_pixels = cv2.countNonZero(roi)
                                area = (cell['inner'][2] - cell['inner'][0]) * (cell['inner'][3] - cell['inner'][1])
                                col_ratios.append((black_pixels / area) * 100)
                                
                            max_val = max(col_ratios)
                            if max_val > threshold_val:
                                id_marks.append(str(col_ratios.index(max_val)))
                            else:
                                id_marks.append("X")
                        
                        if len(id_marks) >= 7:
                            t_code = "".join(id_marks[0:2])
                            sc_code = "".join(id_marks[2:4])
                            st_code = "".join(id_marks[5:7])
                            
                            t_name = teacher_dict.get(t_code, f"미상({t_code})")
                            sc_name = school_dict.get(sc_code, f"미상({sc_code})")
                            st_name = student_dict.get(st_code, f"미상({st_code})")
                            
                            student_info = f"{st_name}_{t_name}_{sc_name}"
                        else:
                            student_info = "".join(id_marks)
                        
                    elif b['type'] == '객관식 문항':
                        for r_idx in range(b['rows']):
                            q_num = b['start_q'] + r_idx
                            row_ratios = []
                            for c_idx in range(b['cols']):
                                cell = grid[r_idx][c_idx]
                                roi = thresh[cell['inner'][1]:cell['inner'][3], cell['inner'][0]:cell['inner'][2]]
                                black_pixels = cv2.countNonZero(roi)
                                area = (cell['inner'][2] - cell['inner'][0]) * (cell['inner'][3] - cell['inner'][1])
                                row_ratios.append((black_pixels / area) * 100)
                                
                            marked_indices = [i for i, val in enumerate(row_ratios) if val > threshold_val]
                            
                            if len(marked_indices) == 1:
                                student_answers[q_num] = marked_indices[0] + 1
                            elif len(marked_indices) > 1:
                                student_answers[q_num] = -1 
                            else:
                                student_answers[q_num] = 0 
                                
                            grid[r_idx][0]['_row_ratios'] = row_ratios
                            
                    elif b['type'] == '수학 단답형 (1문항)':
                        q_num = b['start_q']
                        col_marks = []
                        is_multiple = False
                        
                        for c_idx in range(3):
                            col_ratios = []
                            for r_idx in range(10):
                                cell = grid[r_idx][c_idx]
                                roi = thresh[cell['inner'][1]:cell['inner'][3], cell['inner'][0]:cell['inner'][2]]
                                black_pixels = cv2.countNonZero(roi)
                                area = (cell['inner'][2] - cell['inner'][0]) * (cell['inner'][3] - cell['inner'][1])
                                col_ratios.append((black_pixels / area) * 100)
                                cell['_ratio'] = col_ratios[-1]
                                
                            marked_indices = [i for i, val in enumerate(col_ratios) if val > threshold_val]
                            
                            if len(marked_indices) == 1:
                                col_marks.append(marked_indices[0])
                            elif len(marked_indices) > 1:
                                is_multiple = True
                                col_marks.append(-1)
                            else:
                                col_marks.append(-2)
                                
                        if is_multiple:
                            student_answers[q_num] = -1 
                        elif all(m == -2 for m in col_marks):
                            student_answers[q_num] = -2 
                        else:
                            h = col_marks[0] if col_marks[0] != -2 else 0
                            t = col_marks[1] if col_marks[1] != -2 else 0
                            u = col_marks[2] if col_marks[2] != -2 else 0
                            student_answers[q_num] = (h * 100) + (t * 10) + u

                total_score = 0
                incorrect_qs = []
                
                for q_num in range(1, len(answer_key) + 1):
                    if q_num not in answer_key or q_num not in student_answers:
                        continue
                        
                    s_ans = student_answers[q_num]
                    c_ans = answer_key[q_num]['answer']
                    pt = answer_key[q_num]['point']
                    
                    is_correct = (s_ans == c_ans)
                    if is_correct:
                        total_score += pt
                    else:
                        incorrect_qs.append(str(q_num))
                        
                for b in st.session_state.boxes:
                    r = b['rect']
                    grid = get_grid_absolute(r['left'], r['top'], r['left'] + r['width'], r['top'] + r['height'], b['rows'], b['cols'])
                    
                    if b['type'] == '객관식 문항':
                        for r_idx in range(b['rows']):
                            q_num = b['start_q'] + r_idx
                            if q_num in student_answers:
                                s_ans = student_answers[q_num]
                                ratios = grid[r_idx][0].get('_row_ratios', [])
                                
                                if s_ans > 0:
                                    is_correct = (s_ans == answer_key.get(q_num, {}).get('answer', -1))
                                    color = (0, 255, 0) if is_correct else (0, 0, 255)
                                    cell = grid[r_idx][s_ans - 1]
                                    cv2.rectangle(img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), color, 3)
                                elif s_ans == 0:
                                    cell = grid[r_idx][0]
                                    cv2.rectangle(img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), (0, 0, 255), 3)
                                elif s_ans == -1:
                                    for c_idx, ratio in enumerate(ratios):
                                        if ratio > threshold_val:
                                            cell = grid[r_idx][c_idx]
                                            cv2.rectangle(img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), (0, 0, 255), 3)

                    elif b['type'] == '수학 단답형 (1문항)':
                        q_num = b['start_q']
                        if q_num in student_answers:
                            s_ans = student_answers[q_num]
                            is_correct = (s_ans == answer_key.get(q_num, {}).get('answer', -1))
                            
                            if is_correct:
                                for c_idx in range(b['cols']):
                                    for r_idx in range(b['rows']):
                                        cell = grid[r_idx][c_idx]
                                        ratio = cell.get('_ratio', 0)
                                        if ratio > threshold_val:
                                            cv2.rectangle(img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), (0, 255, 0), 3)
                            else:
                                # 오답일 경우 (단순 오답, 복수 기입, 완전 미기입 포함) 모두 최상단 0 위치에 빨간 박스 표시
                                for c_idx in range(b['cols']):
                                    cell = grid[0][c_idx]
                                    cv2.rectangle(img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), (0, 0, 255), 3)
                                    
                                # 미기입이 아닌 경우, 학생이 마킹한 오답 위치에도 추가로 빨간 박스 표시하여 어디를 틀렸는지 확인
                                if s_ans != -2:
                                    for c_idx in range(b['cols']):
                                        for r_idx in range(b['rows']):
                                            cell = grid[r_idx][c_idx]
                                            ratio = cell.get('_ratio', 0)
                                            if ratio > threshold_val:
                                                cv2.rectangle(img, (cell['outer'][0], cell['outer'][1]), (cell['outer'][2], cell['outer'][3]), (0, 0, 255), 3)

                all_results.append({
                    "학생 정보": student_info,
                    "총점": total_score,
                    "틀린 문항": ", ".join(incorrect_qs) if incorrect_qs else "없음",
                    "파일명": pdf_file.name
                })
                
                progress_bar.progress((idx + 1) / len(test_files))
                
                with col2:
                    st.subheader(f"📄 {student_info} | {total_score}점")
                    st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_container_width=True)
                    
            st.success("🎉 대량 채점 완료!")
            df_all = pd.DataFrame(all_results)
            
            import io
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_all.to_excel(writer, index=False, sheet_name='채점결과')
            
            st.download_button(
                label="📊 학생별 최종 점수 다운로드 (.xlsx)",
                data=excel_buffer.getvalue(),
                file_name="OMR_최종_성적표_V11.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
