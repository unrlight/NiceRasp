import requests
import json
from datetime import timedelta, date

gruppa = "МПО02-24-01"
beginweek = 1
endweek = 20
combine_subgroups = 0  # 0 — делить по подгруппам, 1 — объединять подгруппы

def get_schedule(gruppa, beginweek, endweek):
    url = "https://raspisanie.rusoil.net/origins/get_rasp_student"
    payload = {
        "gruppa": gruppa,
        "beginweek": beginweek,
        "endweek": endweek
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Ошибка при получении данных: {response.status_code}")

def get_dates_by_week_day_and_pair(beginweek, endweek, dayweek, para):
    start_date = date(2024, 9, 2)
    dates = []
    
    for week in range(beginweek, endweek + 1):
        days_offset = (week - 1) * 7 + (dayweek - 1)
        lesson_date = start_date + timedelta(days=days_offset)
        
        lesson_time = {
            1: "08:45-10:20",
            2: "10:30-12:05",
            3: "12:15-13:50",
            4: "14:35-16:10",
            5: "16:20-17:55",
            6: "18:05-19:40",
            7: "19:50-21:15"
        }
        
        date_str = lesson_date.strftime("%d.%m")
        time_str = lesson_time.get(para, "Неизвестное время")
        dates.append((date_str, time_str, week))
    
    return dates

def sort_lessons_by_date(lessons):
    return sorted(lessons, key=lambda lesson: (
        lesson["BEGINWEEK"], lesson["DAYWEEK"], lesson["PARA"]
    ))

def generate_markdown_table(schedule):
    subjects = {}

    for lesson in schedule:
        subject = lesson["NDISC"]
        podgruppa = lesson["PODGRUPPA"] or "Общая"
        
        if combine_subgroups == 1:
            podgruppa = "Общая"
        
        if subject not in subjects:
            subjects[subject] = {}
        
        vidzanat = lesson["NVIDZANAT"]
        if vidzanat not in subjects[subject]:
            subjects[subject][vidzanat] = {}
        
        if podgruppa not in subjects[subject][vidzanat]:
            subjects[subject][vidzanat][podgruppa] = []
        
        subjects[subject][vidzanat][podgruppa].append(lesson)
    
    for subject, lessons_by_type in subjects.items():
        print(f"## {subject}")
        
        for vidzanat, lessons_by_podgruppa in lessons_by_type.items():
            if vidzanat == "лекция":
                type_name = "Лекции"
            elif vidzanat == "практическое занятие":
                type_name = "Практики"
            elif vidzanat == "лаб.работа":
                type_name = "Лабораторные работы"
            else:
                type_name = "Другие"

            print(f"### {type_name}")
            
            for podgruppa, lessons in lessons_by_podgruppa.items():
                if combine_subgroups == 0 and podgruppa != "Общая" and len(lessons_by_podgruppa) > 1:
                    print(f"#### Подгруппа {podgruppa}")
                
                print("| №  | Дата  | Время | Кабинет | Преподаватель | Неделя |")
                print("|----|-------|-------|---------|---------------|--------|")
                
                sorted_lessons = sort_lessons_by_date(lessons)
                lesson_counter = 0
                
                for lesson in sorted_lessons:
                    lesson_counter += 1
                    dates = get_dates_by_week_day_and_pair(lesson["BEGINWEEK"], lesson["ENDWEEK"], lesson["DAYWEEK"], lesson["PARA"])
                    for date_str, time_str, week in dates:
                        aud = lesson["AUD"] if lesson["AUD"] != "-" else "-"
                        teacher = lesson.get("FIO", "Неизвестно")
                        print(f"| {lesson_counter} | {date_str} | {time_str} | {aud} | {teacher} | {week} |")
                
        print("\n")

def main():
    try:
        all_lessons = []
        for week in range(beginweek, endweek + 1):
            schedule = get_schedule(gruppa, week, week)
            all_lessons.extend(schedule)
        
        generate_markdown_table(all_lessons)
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    main()
