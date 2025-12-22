# نظام تقييم ومراجعات المنتجات

نظام REST API لتقييم و مراجعات المنتجات باستخدام Django REST Framework.

## المميزات


- إدارة المراجعات مع موافقة المشرف
- حساب متوسط التقييمات لكل منتج
- تصفية المراجعات حسب التقييم
- توثيق باستخدام JWT
- صلاحيات محددة للمستخدمين والمشرفين
- نظام تقييم بالنجوم (1-5)
- المشاعر التلقائي للمراجعات
-تصفية المحتوى المسيء باستخدام كلمات محظورة
-نظام تفاعل المستخدمين (إعجابات/عدم إعجاب)
-نظام إشعارات للمستخدمين
-لوحة تحكم إدارية متكاملة
-تحليلات وإحصائيات متقدمة


### الميزات الرئيسية
#### للمستخدمين العاديين
- إنشاء حساب مستخدم جديد
- إضافة مراجعات وتقييمات للمنتجات
- التعليق على المراجعات
- التصويت على المراجعات (مفيد/غير مفيد)
- الإبلاغ عن المراجعات غير الملائمة
- تلقي الإشعارات
- عرض التحليلات والإحصائيات

#### للمدراء
- إدارة المنتجات
- إدارة الكلمات المحظورة
- الموافقة على المراجعات أو إخفائها
- عرض المراجعات التي تحتوي على محتوى مسيء
- تصدير بيانات المراجعات بتنسيقات مختلفة (CSV, Excel)
- عرض التقارير والإحصائيات



## المتطلبات

- Python 3.8+
- Django 3.2+
- Django REST Framework
- Simple JWT

## التنصيب

1-نسخ المشروع
   ``` bash
   git clone https://github.com/Sabahx/product-reviews-api
   cd product-reviews-api
```
2-إنشاء بيئة افتراضية وتثبيت المتطلبات:

``` bash
python -m venv venv
venv\Scripts\activate    
pip install -r requirements.txt
```
3-تنفيذ migrations:

``` bash
python manage.py makemigrations
python manage.py migrate
```
4-تشغيل الخادم:

``` bash
python manage.py runserver
```

# Product Reviews & Ratings API

A production-ready REST API for managing product reviews and star ratings, built with a strong focus on **trust, moderation, and data integrity**.  
The system enables users to submit reviews and ratings while providing administrators with tools to moderate content, ensure quality, and extract business insights.

---

## Purpose

This project demonstrates how a real-world review platform backend can be designed to:
- Ensure **reliable and trustworthy user feedback**
- Support **moderation workflows** for safe content
- Maintain **data integrity and platform credibility**
- Enable **analytics-driven decision making**

---

## Core Features

### User Capabilities
- User registration and authentication using JWT
- Submit product reviews and star ratings (1–5)
- Comment on reviews
- Vote on reviews (helpful / not helpful)
- Report inappropriate or misleading reviews
- Receive notifications related to review activity

### Admin Capabilities
- Product management
- Review moderation (approve, hide, reject)
- Content safety via blocked/banned words
- Monitor flagged and reported reviews
- Analytics and reporting
- Export review data (CSV / Excel)

---

## Tech Stack

- **Backend:** Django, Django REST Framework  
- **Authentication:** JWT (SimpleJWT)  
- **Database:** PostgreSQL / SQLite  
- **Language:** Python  

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Sabahx/product-reviews-api.git
cd product-reviews-api

